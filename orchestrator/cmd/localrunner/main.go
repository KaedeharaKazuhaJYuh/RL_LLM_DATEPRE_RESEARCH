// localrunner starts one allowlisted V4 experiment and records its result.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type spec struct {
	SchemaVersion       string `json:"schema_version"`
	ExperimentID        string `json:"experiment_id"`
	Entrypoint          string `json:"entrypoint"`
	Protocol            string `json:"protocol"`
	Resource            string `json:"resource"`
	Model               string `json:"model,omitempty"`
	Adapter             string `json:"adapter,omitempty"`
	Limit               int    `json:"limit,omitempty"`
	BothFaults          bool   `json:"both_faults,omitempty"`
	ExpectedStepsSHA256 string `json:"expected_steps_sha256,omitempty"`
}

type result struct {
	SchemaVersion  string            `json:"schema_version"`
	ExperimentID   string            `json:"experiment_id"`
	Entrypoint     string            `json:"entrypoint"`
	Status         string            `json:"status"`
	GitCommit      string            `json:"git_commit,omitempty"`
	GitDirty       bool              `json:"git_dirty"`
	StartedAt      string            `json:"started_at"`
	EndedAt        string            `json:"ended_at"`
	ElapsedSeconds float64           `json:"elapsed_seconds"`
	ExitCode       int               `json:"exit_code"`
	Error          string            `json:"error,omitempty"`
	Hashes         map[string]string `json:"hashes"`
}

func validate(s spec) error {
	if s.SchemaVersion != "v4-local-experiment-1" || s.ExperimentID == "" || s.Protocol == "" {
		return errors.New("schema_version, experiment_id and protocol are required")
	}
	if strings.ContainsAny(s.ExperimentID, `/\\`) || s.ExperimentID == "." || s.ExperimentID == ".." {
		return errors.New("experiment_id must be a simple name")
	}
	if s.Limit < 0 {
		return errors.New("limit must be nonnegative")
	}
	switch s.Entrypoint {
	case "v4_export":
		if s.Resource != "cpu" || s.Model != "" || s.Adapter != "" || s.Limit != 0 || s.BothFaults {
			return errors.New("v4_export requires cpu and no evaluation options")
		}
	case "v4_eval":
		if s.Resource != "gpu" || s.Model == "" || s.ExpectedStepsSHA256 != "" {
			return errors.New("v4_eval requires gpu and model")
		}
	default:
		return errors.New("entrypoint is not allowlisted")
	}
	if s.ExpectedStepsSHA256 != "" {
		if len(s.ExpectedStepsSHA256) != 64 {
			return errors.New("expected_steps_sha256 must be SHA-256")
		}
		if _, err := hex.DecodeString(s.ExpectedStepsSHA256); err != nil {
			return err
		}
	}
	return nil
}

func hashFile(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err = io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func saveJSON(path string, value any) error {
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}

func gitInfo(repo string) (string, bool) {
	commitCmd := exec.Command("git", "rev-parse", "HEAD")
	commitCmd.Dir = repo
	b, err := commitCmd.Output()
	if err != nil {
		return "", true
	}
	statusCmd := exec.Command("git", "status", "--porcelain")
	statusCmd.Dir = repo
	status, err := statusCmd.Output()
	return strings.TrimSpace(string(b)), err != nil || len(status) > 0
}

func run(s spec, python, repo, runDir string) (r result, err error) {
	if err := validate(s); err != nil {
		return result{}, err
	}
	if _, err := os.Stat(runDir); err == nil {
		return result{}, errors.New("run directory already exists")
	} else if !os.IsNotExist(err) {
		return result{}, err
	}
	if err := os.MkdirAll(runDir, 0755); err != nil {
		return result{}, err
	}
	started := time.Now()
	commit, dirty := gitInfo(repo)
	r = result{SchemaVersion: "v4-local-result-1", ExperimentID: s.ExperimentID,
		Entrypoint: s.Entrypoint, Status: "failed", GitCommit: commit, GitDirty: dirty,
		StartedAt: started.UTC().Format(time.RFC3339Nano), ExitCode: -1,
		Hashes: map[string]string{}}
	defer func() {
		r.EndedAt = time.Now().UTC().Format(time.RFC3339Nano)
		r.ElapsedSeconds = time.Since(started).Seconds()
	}()
	if err := saveJSON(filepath.Join(runDir, "spec.json"), s); err != nil {
		return r, err
	}
	protocol := s.Protocol
	if !filepath.IsAbs(protocol) {
		protocol = filepath.Join(repo, protocol)
	}
	protocolHash, err := hashFile(filepath.Join(protocol, "manifest.json"))
	if err != nil {
		return r, err
	}
	r.Hashes["protocol_manifest_sha256"] = protocolHash
	if s.Entrypoint == "v4_eval" {
		for _, item := range []struct{ label, root, name string }{
			{"model_weights_sha256", s.Model, "model.safetensors"},
			{"adapter_weights_sha256", s.Adapter, "adapter_model.safetensors"},
		} {
			if item.root == "" {
				continue
			}
			path := item.root
			if !filepath.IsAbs(path) {
				path = filepath.Join(repo, path)
			}
			if value, hashErr := hashFile(filepath.Join(path, item.name)); hashErr == nil {
				r.Hashes[item.label] = value
			}
		}
	}
	profile := filepath.Join(runDir, "profile.json")
	var module, output string
	var args []string
	if s.Entrypoint == "v4_export" {
		module = "experiments.v4_llm_export"
		output = filepath.Join(runDir, "artifacts")
		args = []string{"-m", module, "--protocol", protocol, "--out", output,
			"--profile-out", profile}
	} else {
		module = "experiments.v4_llm_eval"
		output = filepath.Join(runDir, "result.json")
		args = []string{"-m", module, "--protocol", protocol, "--model", s.Model,
			"--out", output, "--profile-out", profile}
		if s.Adapter != "" {
			args = append(args, "--adapter", s.Adapter)
		}
		if s.Limit > 0 {
			args = append(args, "--limit", fmt.Sprint(s.Limit))
		}
		if s.BothFaults {
			args = append(args, "--both-faults")
		}
	}
	logFile, err := os.Create(filepath.Join(runDir, "runner.log"))
	if err != nil {
		return r, err
	}
	cmd := exec.Command(python, args...)
	cmd.Dir = repo
	cmd.Stdout = logFile
	cmd.Stderr = logFile
	cmdErr := cmd.Run()
	closeErr := logFile.Close()
	if cmd.ProcessState != nil {
		r.ExitCode = cmd.ProcessState.ExitCode()
	}
	if cmdErr != nil {
		return r, cmdErr
	}
	if closeErr != nil {
		return r, closeErr
	}
	paths := map[string]string{"profile_sha256": profile}
	if s.Entrypoint == "v4_export" {
		paths["summary_sha256"] = filepath.Join(output, "summary.json")
		paths["train_steps_sha256"] = filepath.Join(output, "train_steps.jsonl")
	} else {
		paths["result_sha256"] = output
	}
	for label, path := range paths {
		value, err := hashFile(path)
		if err != nil {
			return r, err
		}
		r.Hashes[label] = value
	}
	if s.Entrypoint == "v4_export" {
		b, err := os.ReadFile(filepath.Join(output, "summary.json"))
		if err != nil {
			return r, err
		}
		var summary struct {
			TrainStepsSHA256 string `json:"train_steps_sha256"`
			TrainEpisodes    int    `json:"train_episodes"`
		}
		if err := json.Unmarshal(b, &summary); err != nil {
			return r, err
		}
		if summary.TrainEpisodes < 1 || summary.TrainStepsSHA256 != r.Hashes["train_steps_sha256"] {
			return r, errors.New("export summary does not match training artifact")
		}
	} else {
		b, err := os.ReadFile(output)
		if err != nil {
			return r, err
		}
		var summary struct {
			ProtocolSHA256 string `json:"protocol_sha256"`
			Episodes       int    `json:"episodes"`
			Greedy         bool   `json:"greedy"`
		}
		if err := json.Unmarshal(b, &summary); err != nil {
			return r, err
		}
		if summary.Episodes < 1 || !summary.Greedy || summary.ProtocolSHA256 != protocolHash {
			return r, errors.New("evaluation summary does not match protocol")
		}
	}
	if s.ExpectedStepsSHA256 != "" && r.Hashes["train_steps_sha256"] != s.ExpectedStepsSHA256 {
		return r, errors.New("exported training steps do not match expected SHA-256")
	}
	r.Status = "succeeded"
	return r, nil
}

func main() {
	manifest := flag.String("manifest", "", "versioned experiment spec JSON")
	python := flag.String("python", "python", "Python executable")
	repo := flag.String("repo", ".", "repository root")
	runDir := flag.String("run-dir", "", "new output directory for this run")
	flag.Parse()
	if *manifest == "" || *runDir == "" {
		fmt.Fprintln(os.Stderr, "-manifest and -run-dir are required")
		os.Exit(2)
	}
	repoPath, err := filepath.Abs(*repo)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	runPath, err := filepath.Abs(*runDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	b, err := os.ReadFile(*manifest)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var s spec
	if err := json.Unmarshal(b, &s); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	r, err := run(s, *python, repoPath, runPath)
	if r.SchemaVersion != "" {
		if err != nil {
			r.Error = err.Error()
		}
		if saveErr := saveJSON(filepath.Join(runPath, "result_manifest.json"), r); saveErr != nil {
			fmt.Fprintln(os.Stderr, saveErr)
			os.Exit(1)
		}
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("%s: %s (exit %d)\n", s.ExperimentID, r.Status, r.ExitCode)
}
