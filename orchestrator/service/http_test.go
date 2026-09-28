package service

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"

	"rl-llm-data-agent/orchestrator/queue"
)

func TestHTTPLeaseCancelAndAcknowledgedStop(t *testing.T) {
	q, err := queue.Open(filepath.Join(t.TempDir(), "state.json"))
	if err != nil {
		t.Fatal(err)
	}
	defer q.Close()
	server := httptest.NewServer(&Server{Queue: q})
	defer server.Close()
	post := func(path string, value any, target any) int {
		data, err := json.Marshal(value)
		if err != nil {
			t.Fatal(err)
		}
		res, err := http.Post(server.URL+path, "application/json", bytes.NewReader(data))
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if target != nil && res.StatusCode == 200 {
			if err := json.NewDecoder(res.Body).Decode(target); err != nil {
				t.Fatal(err)
			}
		}
		return res.StatusCode
	}
	spec := json.RawMessage(`{"entrypoint":"v4_eval","resource":"gpu"}`)
	var submitted struct {
		Job       queue.Job `json:"job"`
		Duplicate bool      `json:"duplicate"`
	}
	body := map[string]any{"id": "job1", "submission_key": "same", "resource": "gpu", "device_id": "gpu0", "spec": spec}
	if post("/jobs", body, &submitted) != 200 || submitted.Duplicate {
		t.Fatal("submit failed")
	}
	if post("/jobs", body, &submitted) != 200 || !submitted.Duplicate {
		t.Fatal("duplicate not deduplicated")
	}
	var acquired struct {
		Job   queue.Job `json:"job"`
		Found bool      `json:"found"`
	}
	if post("/lease", map[string]any{"worker_id": "worker0", "resource": "gpu", "device_id": "gpu0", "ttl_seconds": 30}, &acquired) != 200 || !acquired.Found {
		t.Fatal("lease failed")
	}
	id, token := acquired.Job.ID, acquired.Job.Token
	var updated queue.Job
	if post("/jobs/"+id+"/heartbeat", map[string]any{"worker_id": "worker0", "token": token, "ttl_seconds": 30}, &updated) != 200 || updated.Status != "running" {
		t.Fatal("heartbeat failed")
	}
	if post("/jobs/"+id+"/cancel", map[string]any{}, &updated) != 200 || !updated.CancelRequested {
		t.Fatal("cancel not requested")
	}
	if post("/jobs/"+id+"/stopped", map[string]string{"token": token}, &updated) != 200 || updated.Status != "cancelled" {
		t.Fatal("stopped acknowledgement failed")
	}
}
