package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"rl-llm-data-agent/orchestrator/queue"
)

type client struct {
	base string
	http *http.Client
}

func (c client) post(path string, request any, response any) error {
	data, err := json.Marshal(request)
	if err != nil {
		return err
	}
	req, err := http.NewRequest(http.MethodPost, c.base+path, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	reply, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer reply.Body.Close()
	body, err := io.ReadAll(io.LimitReader(reply.Body, 1<<20))
	if err != nil {
		return err
	}
	if reply.StatusCode != 200 {
		return fmt.Errorf("coordinator %s: %s", reply.Status, strings.TrimSpace(string(body)))
	}
	if response != nil {
		return json.Unmarshal(body, response)
	}
	return nil
}

type config struct {
	server, workerID, resource, deviceID, python, repo, runner, outputRoot string
	ttl, heartbeat                                                         time.Duration
}

func (cfg config) runOne(c client) (bool, error) {
	var acquired struct {
		Job   queue.Job `json:"job"`
		Found bool      `json:"found"`
	}
	err := c.post("/lease", map[string]any{"worker_id": cfg.workerID, "resource": cfg.resource,
		"device_id": cfg.deviceID, "ttl_seconds": int(cfg.ttl.Seconds())}, &acquired)
	if err != nil || !acquired.Found {
		return false, err
	}
	job := acquired.Job
	var spec struct {
		Resource   string `json:"resource"`
		Entrypoint string `json:"entrypoint"`
	}
	if err := json.Unmarshal(job.Spec, &spec); err != nil || spec.Resource != job.Resource ||
		!(spec.Entrypoint == "v4_export" || spec.Entrypoint == "v4_eval" || spec.Entrypoint == "v4_eval_npu") {
		c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
		return true, errors.New("leased spec is not an allowlisted matching resource")
	}
	parent := filepath.Join(cfg.outputRoot, job.ID)
	if err := os.MkdirAll(parent, 0755); err != nil {
		return true, err
	}
	manifest := filepath.Join(parent, fmt.Sprintf("attempt-%d-spec.json", job.Attempt))
	runDir := filepath.Join(parent, fmt.Sprintf("attempt-%d", job.Attempt))
	if _, err := os.Stat(manifest); err == nil {
		return true, errors.New("attempt manifest already exists")
	}
	if err := os.WriteFile(manifest, job.Spec, 0644); err != nil {
		return true, err
	}
	cmd := exec.Command(cfg.runner, "-manifest", manifest, "-python", cfg.python,
		"-repo", cfg.repo, "-run-dir", runDir)
	cmd.Dir = cfg.repo
	cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
	tree, err := newProcessTree()
	if err != nil {
		return true, err
	}
	defer tree.close()
	tree.prepare(cmd)
	if err := cmd.Start(); err != nil {
		c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
		return true, err
	}
	if err := tree.attach(cmd); err != nil {
		tree.stop(cmd)
		cmd.Wait()
		c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
		return true, fmt.Errorf("cannot contain process tree: %w", err)
	}
	finished := make(chan error, 1)
	go func() { finished <- cmd.Wait() }()
	ticker := time.NewTicker(cfg.heartbeat)
	defer ticker.Stop()
	for {
		select {
		case err := <-finished:
			if err != nil {
				c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
				return true, fmt.Errorf("local runner failed: %w", err)
			}
			resultPath := filepath.Join(runDir, "result_manifest.json")
			data, err := os.ReadFile(resultPath)
			if err != nil {
				c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
				return true, err
			}
			var result struct {
				Status string `json:"status"`
			}
			if json.Unmarshal(data, &result) != nil || result.Status != "succeeded" {
				c.post("/jobs/"+job.ID+"/fail", map[string]string{"token": job.Token}, nil)
				return true, errors.New("local runner result is not succeeded")
			}
			sum := sha256.Sum256(data)
			hash := hex.EncodeToString(sum[:])
			var committed queue.Job
			err = c.post("/jobs/"+job.ID+"/complete",
				map[string]string{"token": job.Token, "result_hash": hash}, &committed)
			return true, err
		case <-ticker.C:
			var state queue.Job
			err := c.post("/jobs/"+job.ID+"/heartbeat",
				map[string]any{"worker_id": cfg.workerID, "token": job.Token,
					"ttl_seconds": int(cfg.ttl.Seconds())}, &state)
			if err != nil || state.CancelRequested {
				tree.stop(cmd)
				<-finished
				// If the coordinator is unavailable, leave the device quarantined.
				ackErr := c.post("/jobs/"+job.ID+"/stopped", map[string]string{"token": job.Token}, nil)
				if err != nil {
					return true, fmt.Errorf("heartbeat failed; stopped process: %w; ack: %v", err, ackErr)
				}
				return true, ackErr
			}
		}
	}
}

func main() {
	var cfg config
	flag.StringVar(&cfg.server, "server", "http://127.0.0.1:8765", "loopback coordinator URL")
	flag.StringVar(&cfg.workerID, "worker-id", "worker0", "worker identity")
	flag.StringVar(&cfg.resource, "resource", "cpu", "cpu, gpu, or npu")
	flag.StringVar(&cfg.deviceID, "device-id", "", "device identifier for gpu/npu")
	flag.StringVar(&cfg.python, "python", "python", "Python executable")
	flag.StringVar(&cfg.repo, "repo", ".", "repository root")
	flag.StringVar(&cfg.runner, "runner", "localrunner", "allowlisted localrunner executable")
	flag.StringVar(&cfg.outputRoot, "output-root", "work/v5_queue/runs", "attempt output root")
	flag.DurationVar(&cfg.ttl, "ttl", 30*time.Second, "lease lifetime")
	flag.DurationVar(&cfg.heartbeat, "heartbeat", 5*time.Second, "heartbeat interval")
	once := flag.Bool("once", false, "poll once then exit")
	flag.Parse()
	if !strings.HasPrefix(cfg.server, "http://127.0.0.1:") && !strings.HasPrefix(cfg.server, "http://localhost:") {
		log.Fatal("alpha coordinator must use loopback HTTP")
	}
	if cfg.heartbeat <= 0 || cfg.ttl <= 2*cfg.heartbeat || cfg.ttl < time.Second {
		log.Fatal("invalid heartbeat or TTL")
	}
	var err error
	cfg.repo, err = filepath.Abs(cfg.repo)
	if err != nil {
		log.Fatal(err)
	}
	cfg.outputRoot, err = filepath.Abs(cfg.outputRoot)
	if err != nil {
		log.Fatal(err)
	}
	cfg.runner, err = exec.LookPath(cfg.runner)
	if err != nil {
		log.Fatal(err)
	}
	cfg.runner, err = filepath.Abs(cfg.runner)
	if err != nil {
		log.Fatal(err)
	}
	c := client{base: strings.TrimRight(cfg.server, "/"), http: &http.Client{Timeout: 5 * time.Second}}
	for {
		found, err := cfg.runOne(c)
		if err != nil {
			log.Printf("worker: %v", err)
		}
		if *once {
			if err != nil {
				os.Exit(1)
			}
			return
		}
		if !found {
			time.Sleep(2 * time.Second)
		}
	}
}
