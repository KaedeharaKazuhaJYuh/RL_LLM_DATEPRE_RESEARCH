// Package service exposes the durable queue on a loopback HTTP interface.
package service

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"time"

	"rl-llm-data-agent/orchestrator/queue"
)

type Server struct{ Queue *queue.Queue }

func decode(r *http.Request, value any) error {
	reader := json.NewDecoder(http.MaxBytesReader(nil, r.Body, 1<<20))
	reader.DisallowUnknownFields()
	if err := reader.Decode(value); err != nil {
		return err
	}
	var extra any
	if err := reader.Decode(&extra); err != io.EOF {
		return errors.New("request must contain exactly one JSON value")
	}
	return nil
}

func reply(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(value)
}

func fail(w http.ResponseWriter, err error) {
	reply(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	now := time.Now().UTC()
	switch {
	case r.URL.Path == "/jobs" && r.Method == http.MethodGet:
		reply(w, 200, s.Queue.List())
	case r.URL.Path == "/jobs" && r.Method == http.MethodPost:
		var body struct {
			ID            string          `json:"id"`
			SubmissionKey string          `json:"submission_key"`
			Resource      string          `json:"resource"`
			DeviceID      string          `json:"device_id"`
			Spec          json.RawMessage `json:"spec"`
		}
		if err := decode(r, &body); err != nil {
			fail(w, err)
			return
		}
		job, duplicate, err := s.Queue.Submit(body.ID, body.SubmissionKey, body.Resource,
			body.DeviceID, body.Spec, now)
		if err != nil {
			fail(w, err)
			return
		}
		reply(w, 200, map[string]any{"job": job, "duplicate": duplicate})
	case r.URL.Path == "/lease" && r.Method == http.MethodPost:
		var body struct {
			WorkerID   string `json:"worker_id"`
			Resource   string `json:"resource"`
			DeviceID   string `json:"device_id"`
			TTLSeconds int    `json:"ttl_seconds"`
		}
		if err := decode(r, &body); err != nil {
			fail(w, err)
			return
		}
		job, found, err := s.Queue.Acquire(body.WorkerID, body.Resource, body.DeviceID,
			now, time.Duration(body.TTLSeconds)*time.Second)
		if err != nil {
			fail(w, err)
			return
		}
		reply(w, 200, map[string]any{"job": job, "found": found})
	case strings.HasPrefix(r.URL.Path, "/jobs/"):
		rest := strings.TrimPrefix(r.URL.Path, "/jobs/")
		pieces := strings.Split(rest, "/")
		if len(pieces) == 1 && r.Method == http.MethodGet {
			job, ok := s.Queue.Get(pieces[0])
			if !ok {
				http.NotFound(w, r)
				return
			}
			reply(w, 200, job)
			return
		}
		if len(pieces) != 2 || r.Method != http.MethodPost {
			http.NotFound(w, r)
			return
		}
		id, action := pieces[0], pieces[1]
		var err error
		var job queue.Job
		switch action {
		case "heartbeat":
			var body struct {
				WorkerID   string `json:"worker_id"`
				Token      string `json:"token"`
				TTLSeconds int    `json:"ttl_seconds"`
			}
			if err = decode(r, &body); err == nil {
				job, err = s.Queue.Heartbeat(id, body.WorkerID, body.Token,
					now, time.Duration(body.TTLSeconds)*time.Second)
			}
		case "complete":
			var body struct {
				Token      string `json:"token"`
				ResultHash string `json:"result_hash"`
			}
			if err = decode(r, &body); err == nil {
				job, err = s.Queue.Complete(id, body.Token, body.ResultHash, now)
			}
		case "fail":
			var body struct {
				Token string `json:"token"`
			}
			if err = decode(r, &body); err == nil {
				job, err = s.Queue.Fail(id, body.Token, now)
			}
		case "cancel":
			job, err = s.Queue.Cancel(id, now)
		case "stopped":
			var body struct {
				Token string `json:"token"`
			}
			if err = decode(r, &body); err == nil {
				job, err = s.Queue.AcknowledgeStopped(id, body.Token, now)
			}
		case "recover":
			var body struct {
				ConfirmedStopped bool `json:"confirmed_stopped"`
			}
			if err = decode(r, &body); err == nil {
				if !body.ConfirmedStopped {
					reply(w, 400, map[string]string{"error": "confirmed_stopped must be true"})
					return
				}
				job, err = s.Queue.ConfirmCleanup(id, now)
			}
		default:
			http.NotFound(w, r)
			return
		}
		if err != nil {
			fail(w, err)
			return
		}
		reply(w, 200, job)
	default:
		http.NotFound(w, r)
	}
}
