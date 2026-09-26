package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSpecRejectsArbitraryEntrypoint(t *testing.T) {
	s := spec{SchemaVersion: "v4-local-experiment-1", ExperimentID: "safe",
		Entrypoint: "../../shell", Protocol: "tasks/v4/llm_composition_v1", Resource: "cpu"}
	if err := validate(s); err == nil {
		t.Fatal("arbitrary module was accepted")
	}
	s.Entrypoint = "v4_export"
	if err := validate(s); err != nil {
		t.Fatal(err)
	}
}

func TestRunRefusesExistingOutputBeforeStartingPython(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "existing")
	if err := os.Mkdir(dir, 0755); err != nil {
		t.Fatal(err)
	}
	s := spec{SchemaVersion: "v4-local-experiment-1", ExperimentID: "safe",
		Entrypoint: "v4_export", Protocol: "tasks/v4/llm_composition_v1", Resource: "cpu"}
	if _, err := run(s, "python-does-not-exist", t.TempDir(), dir); err == nil {
		t.Fatal("existing output was overwritten")
	}
}
