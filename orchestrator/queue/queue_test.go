package queue

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func newQueue(t *testing.T) (*Queue, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "state.json")
	q, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { q.Close() })
	return q, path
}

func submit(t *testing.T, q *Queue, id string, when time.Time) {
	t.Helper()
	if _, _, err := q.Submit(id, id+"_key", "gpu", "gpu0", json.RawMessage(`{"entrypoint":"v4_eval"}`), when); err != nil {
		t.Fatal(err)
	}
}

func TestPersistIdempotencyAndSingleCoordinator(t *testing.T) {
	q, path := newQueue(t)
	now := time.Now()
	job, duplicate, err := q.Submit("one", "key1", "gpu", "gpu0", json.RawMessage(`{"a":1,"b":2}`), now)
	if err != nil || duplicate || job.Status != "queued" {
		t.Fatalf("first submit: %+v %v", job, err)
	}
	_, duplicate, err = q.Submit("one", "key1", "gpu", "gpu0", json.RawMessage(`{"b":2,"a":1}`), now)
	if err != nil || !duplicate {
		t.Fatal("retry was not idempotent", err)
	}
	if _, _, err := q.Submit("two", "key1", "gpu", "gpu0", json.RawMessage(`{"a":1}`), now); err == nil {
		t.Fatal("conflicting idempotency key accepted")
	}
	if _, err := Open(path); err == nil {
		t.Fatal("second coordinator acquired same state")
	}
	if err := q.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	if got, ok := reopened.Get("one"); !ok || got.Status != "queued" {
		t.Fatalf("lost persisted job: %+v", got)
	}
}

func TestLeaseExclusivityCancellationAndFencing(t *testing.T) {
	q, _ := newQueue(t)
	now := time.Now()
	submit(t, q, "one", now)
	submit(t, q, "two", now.Add(time.Second))
	first, ok, err := q.Acquire("workerA", "gpu", "gpu0", now, 10*time.Second)
	if err != nil || !ok || first.ID != "one" || first.Attempt != 1 {
		t.Fatal(first, ok, err)
	}
	if _, ok, _ := q.Acquire("workerB", "gpu", "gpu0", now, 10*time.Second); ok {
		t.Fatal("same device leased twice")
	}
	first, err = q.Heartbeat(first.ID, "workerA", first.Token, now.Add(time.Second), 10*time.Second)
	if err != nil || first.Status != "running" {
		t.Fatal(err)
	}
	cancelled, err := q.Cancel(first.ID, now.Add(2*time.Second))
	if err != nil || !cancelled.CancelRequested {
		t.Fatal(err)
	}
	if _, err := q.Complete(first.ID, first.Token, strings.Repeat("a", 64), now.Add(3*time.Second)); err == nil {
		t.Fatal("cancelled job accepted completion")
	}
	if _, ok, _ := q.Acquire("workerB", "gpu", "gpu0", now.Add(3*time.Second), time.Second); ok {
		t.Fatal("cancel request released device before child stopped")
	}
	if _, err := q.AcknowledgeStopped(first.ID, first.Token, now.Add(4*time.Second)); err != nil {
		t.Fatal(err)
	}
	second, ok, err := q.Acquire("workerB", "gpu", "gpu0", now.Add(5*time.Second), time.Second)
	if err != nil || !ok || second.ID != "two" {
		t.Fatal(second, err)
	}
	hash := strings.Repeat("b", 64)
	if _, err := q.Complete(second.ID, second.Token, hash, now.Add(5500*time.Millisecond)); err != nil {
		t.Fatal(err)
	}
	if _, err := q.Complete(second.ID, second.Token, hash, now.Add(6*time.Second)); err != nil {
		t.Fatal("idempotent finish failed", err)
	}
	if _, err := q.Complete(second.ID, second.Token, strings.Repeat("c", 64), now.Add(6*time.Second)); err == nil {
		t.Fatal("different result overwrote final result")
	}
}

func TestLostLeaseQuarantinesDeviceUntilCleanupThenRetries(t *testing.T) {
	q, path := newQueue(t)
	now := time.Now()
	submit(t, q, "one", now)
	submit(t, q, "two", now.Add(time.Second))
	first, ok, err := q.Acquire("workerA", "gpu", "gpu0", now, time.Second)
	if err != nil || !ok {
		t.Fatal(err)
	}
	lost, err := q.Reap(now.Add(2 * time.Second))
	if err != nil || len(lost) != 1 || lost[0].Status != "lost" {
		t.Fatal(lost, err)
	}
	if _, err := q.Complete(first.ID, first.Token, strings.Repeat("a", 64), now.Add(2*time.Second)); err == nil {
		t.Fatal("expired attempt committed result")
	}
	if _, ok, _ := q.Acquire("workerB", "gpu", "gpu0", now.Add(2*time.Second), time.Second); ok {
		t.Fatal("lost process did not quarantine device")
	}
	q.Close()
	q, err = Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer q.Close()
	if _, err := q.ConfirmCleanup("one", now.Add(3*time.Second)); err != nil {
		t.Fatal(err)
	}
	next, ok, err := q.Acquire("workerB", "gpu", "gpu0", now.Add(4*time.Second), time.Second)
	if err != nil || !ok || next.ID != "two" {
		t.Fatal(next, ok, err)
	}
	if _, err := q.Complete(next.ID, first.Token, strings.Repeat("b", 64), now.Add(4500*time.Millisecond)); err == nil {
		t.Fatal("late old token accepted")
	}
	if _, err := q.Fail(next.ID, next.Token, now.Add(4500*time.Millisecond)); err != nil {
		t.Fatal(err)
	}
	retry, ok, err := q.Acquire("workerC", "gpu", "gpu0", now.Add(5*time.Second), time.Second)
	if err != nil || !ok || retry.ID != "one" || retry.Attempt != 2 || retry.Token == first.Token {
		t.Fatal("recovered job did not receive new fenced attempt", retry, err)
	}
}

func TestQueuedCancellationAndValidation(t *testing.T) {
	q, _ := newQueue(t)
	now := time.Now()
	submit(t, q, "one", now)
	if _, err := q.Cancel("one", now); err != nil {
		t.Fatal(err)
	}
	if _, ok, _ := q.Acquire("w", "gpu", "gpu0", now, time.Second); ok {
		t.Fatal("cancelled job leased")
	}
	if _, _, err := q.Submit("../bad", "bad", "gpu", "gpu0", json.RawMessage(`{}`), now); err == nil {
		t.Fatal("path-like job ID accepted")
	}
}
