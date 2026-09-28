// Package queue implements a single-coordinator durable experiment queue.
package queue

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

type Job struct {
	ID              string          `json:"id"`
	SubmissionKey   string          `json:"submission_key"`
	Resource        string          `json:"resource"`
	DeviceID        string          `json:"device_id"`
	Spec            json.RawMessage `json:"spec"`
	Status          string          `json:"status"`
	Attempt         uint64          `json:"attempt"`
	Token           string          `json:"token,omitempty"`
	WorkerID        string          `json:"worker_id,omitempty"`
	LeaseUntil      time.Time       `json:"lease_until,omitempty"`
	CancelRequested bool            `json:"cancel_requested,omitempty"`
	ResultHash      string          `json:"result_hash,omitempty"`
	UpdatedAt       time.Time       `json:"updated_at"`
}

type snapshot struct {
	Version int               `json:"version"`
	Jobs    map[string]Job    `json:"jobs"`
	Keys    map[string]string `json:"keys"`
}

type Queue struct {
	mu       sync.Mutex
	path     string
	lockFile *os.File
	state    snapshot
}

func Open(path string) (*Queue, error) {
	absolute, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Dir(absolute), 0755); err != nil {
		return nil, err
	}
	lockPath := absolute + ".lock"
	lock, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return nil, fmt.Errorf("open queue lock: %w", err)
	}
	if err := lockQueueFile(lock); err != nil {
		lock.Close()
		return nil, fmt.Errorf("queue already open or locked: %w", err)
	}
	q := &Queue{path: absolute, lockFile: lock,
		state: snapshot{Version: 1, Jobs: map[string]Job{}, Keys: map[string]string{}}}
	if raw, err := os.ReadFile(absolute); err == nil {
		if json.Unmarshal(raw, &q.state) != nil || q.state.Version != 1 ||
			q.state.Jobs == nil || q.state.Keys == nil {
			lock.Close()
			return nil, errors.New("invalid queue snapshot")
		}
	} else if !os.IsNotExist(err) {
		lock.Close()
		return nil, err
	} else if err := q.persist(q.state); err != nil {
		lock.Close()
		return nil, err
	}
	return q, nil
}

func (q *Queue) Close() error {
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.lockFile == nil {
		return nil
	}
	err := q.lockFile.Close()
	q.lockFile = nil
	return err
}

func (q *Queue) persist(state snapshot) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	temporary, err := os.CreateTemp(filepath.Dir(q.path), ".queue-*")
	if err != nil {
		return err
	}
	name := temporary.Name()
	defer os.Remove(name)
	if _, err = temporary.Write(append(data, '\n')); err == nil {
		err = temporary.Sync()
	}
	closeErr := temporary.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	return os.Rename(name, q.path)
}

func (q *Queue) update(change func(*snapshot) error) error {
	raw, err := json.Marshal(q.state)
	if err != nil {
		return err
	}
	var next snapshot
	if err := json.Unmarshal(raw, &next); err != nil {
		return err
	}
	if err := change(&next); err != nil {
		return err
	}
	if err := q.persist(next); err != nil {
		return err
	}
	q.state = next
	return nil
}

func validName(name string) bool {
	if name == "" || len(name) > 128 {
		return false
	}
	for _, r := range name {
		if !(r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' ||
			r >= '0' && r <= '9' || r == '-' || r == '_') {
			return false
		}
	}
	return true
}

func canonicalSpec(spec json.RawMessage) (json.RawMessage, error) {
	var value any
	if err := json.Unmarshal(spec, &value); err != nil {
		return nil, err
	}
	if _, ok := value.(map[string]any); !ok {
		return nil, errors.New("spec must be a JSON object")
	}
	return json.Marshal(value)
}

func (q *Queue) Submit(id, key, resource, device string, spec json.RawMessage, now time.Time) (Job, bool, error) {
	if !validName(id) || !validName(key) ||
		!(resource == "cpu" || resource == "gpu" || resource == "npu") ||
		(resource == "cpu" && device != "") || (resource != "cpu" && !validName(device)) {
		return Job{}, false, errors.New("invalid id, key, resource or device")
	}
	normalized, err := canonicalSpec(spec)
	if err != nil {
		return Job{}, false, err
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	if existingID, ok := q.state.Keys[key]; ok {
		existing := q.state.Jobs[existingID]
		if existing.ID != id || existing.Resource != resource || existing.DeviceID != device ||
			string(existing.Spec) != string(normalized) {
			return Job{}, false, errors.New("submission key conflicts with existing job")
		}
		return existing, true, nil
	}
	if _, exists := q.state.Jobs[id]; exists {
		return Job{}, false, errors.New("job id already exists")
	}
	job := Job{ID: id, SubmissionKey: key, Resource: resource, DeviceID: device,
		Spec: normalized, Status: "queued", UpdatedAt: now.UTC()}
	err = q.update(func(next *snapshot) error {
		next.Jobs[id] = job
		next.Keys[key] = id
		return nil
	})
	return job, false, err
}

func (q *Queue) Get(id string) (Job, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	return job, ok
}

func (q *Queue) List() []Job {
	q.mu.Lock()
	defer q.mu.Unlock()
	jobs := make([]Job, 0, len(q.state.Jobs))
	for _, job := range q.state.Jobs {
		jobs = append(jobs, job)
	}
	sort.Slice(jobs, func(i, j int) bool {
		if jobs[i].UpdatedAt.Equal(jobs[j].UpdatedAt) {
			return jobs[i].ID < jobs[j].ID
		}
		return jobs[i].UpdatedAt.Before(jobs[j].UpdatedAt)
	})
	return jobs
}

func occupies(job Job) bool {
	return job.Status == "leased" || job.Status == "running" || job.Status == "lost"
}

func (q *Queue) Acquire(worker, resource, device string, now time.Time, ttl time.Duration) (Job, bool, error) {
	if !validName(worker) || ttl <= 0 {
		return Job{}, false, errors.New("invalid worker or lease TTL")
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	for _, job := range q.state.Jobs {
		if job.Resource == resource && job.DeviceID == device && occupies(job) {
			return Job{}, false, nil // Lost devices remain quarantined until cleanup is confirmed.
		}
	}
	var selected *Job
	for _, job := range q.state.Jobs {
		if job.Status != "queued" || job.Resource != resource || job.DeviceID != device {
			continue
		}
		if selected == nil || job.UpdatedAt.Before(selected.UpdatedAt) ||
			(job.UpdatedAt.Equal(selected.UpdatedAt) && job.ID < selected.ID) {
			candidate := job
			selected = &candidate
		}
	}
	if selected == nil {
		return Job{}, false, nil
	}
	job := *selected
	job.Status = "leased"
	job.Attempt++
	job.Token = fmt.Sprintf("%s-%d", job.ID, job.Attempt)
	job.WorkerID = worker
	job.LeaseUntil = now.Add(ttl).UTC()
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[job.ID] = job; return nil })
	return job, err == nil, err
}

func (q *Queue) Heartbeat(id, worker, token string, now time.Time, ttl time.Duration) (Job, error) {
	if ttl <= 0 {
		return Job{}, errors.New("invalid lease TTL")
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok || job.WorkerID != worker || job.Token != token ||
		!(job.Status == "leased" || job.Status == "running") || !now.Before(job.LeaseUntil) {
		return Job{}, errors.New("stale or expired lease")
	}
	job.Status = "running"
	job.LeaseUntil = now.Add(ttl).UTC()
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func (q *Queue) Complete(id, token, resultHash string, now time.Time) (Job, error) {
	if len(resultHash) != 64 {
		return Job{}, errors.New("result hash must be SHA-256")
	}
	if _, err := hex.DecodeString(resultHash); err != nil {
		return Job{}, err
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok || job.Token != token {
		return Job{}, errors.New("stale fencing token")
	}
	if job.Status == "succeeded" && job.ResultHash == resultHash {
		return job, nil
	}
	if !(job.Status == "leased" || job.Status == "running") ||
		job.CancelRequested || !now.Before(job.LeaseUntil) {
		return Job{}, errors.New("lease cannot complete")
	}
	job.Status, job.ResultHash = "succeeded", resultHash
	job.LeaseUntil = time.Time{}
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func (q *Queue) Fail(id, token string, now time.Time) (Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok || job.Token != token || !(job.Status == "leased" || job.Status == "running") ||
		!now.Before(job.LeaseUntil) {
		return Job{}, errors.New("stale or expired lease")
	}
	job.Status = "failed"
	job.LeaseUntil = time.Time{}
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func (q *Queue) Cancel(id string, now time.Time) (Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok {
		return Job{}, errors.New("unknown job")
	}
	if job.Status == "queued" {
		job.Status = "cancelled"
	} else if job.Status == "leased" || job.Status == "running" {
		job.CancelRequested = true
	} else if job.Status != "cancelled" {
		return Job{}, errors.New("job cannot be cancelled in current state")
	}
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func (q *Queue) AcknowledgeStopped(id, token string, now time.Time) (Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok || job.Token != token || !(job.Status == "leased" || job.Status == "running" || job.Status == "lost") {
		return Job{}, errors.New("stale fencing token")
	}
	if job.Status == "lost" && !job.CancelRequested {
		job.Status = "queued" // A new attempt is issued on the next Acquire.
	} else {
		job.Status = "cancelled"
	}
	job.LeaseUntil = time.Time{}
	job.WorkerID = ""
	job.Token = ""
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func (q *Queue) Reap(now time.Time) ([]Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	hasExpired := false
	for _, job := range q.state.Jobs {
		if (job.Status == "leased" || job.Status == "running") && !now.Before(job.LeaseUntil) {
			hasExpired = true
			break
		}
	}
	if !hasExpired {
		return nil, nil
	}
	lost := []Job{}
	err := q.update(func(next *snapshot) error {
		for id, job := range next.Jobs {
			if (job.Status == "leased" || job.Status == "running") && !now.Before(job.LeaseUntil) {
				job.Status = "lost"
				job.UpdatedAt = now.UTC()
				next.Jobs[id] = job
				lost = append(lost, job)
			}
		}
		return nil
	})
	return lost, err
}

func (q *Queue) ConfirmCleanup(id string, now time.Time) (Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	job, ok := q.state.Jobs[id]
	if !ok || job.Status != "lost" {
		return Job{}, errors.New("only lost jobs can be recovered")
	}
	if job.CancelRequested {
		job.Status = "cancelled"
	} else {
		job.Status = "queued"
	}
	job.Token, job.WorkerID = "", ""
	job.LeaseUntil = time.Time{}
	job.UpdatedAt = now.UTC()
	err := q.update(func(next *snapshot) error { next.Jobs[id] = job; return nil })
	return job, err
}

func Hash(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}
