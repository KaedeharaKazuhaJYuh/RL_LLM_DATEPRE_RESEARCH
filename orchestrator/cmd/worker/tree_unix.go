//go:build !windows

package main

import (
	"os/exec"
	"syscall"
)

type processTree struct{}

func newProcessTree() (*processTree, error) { return &processTree{}, nil }
func (tree *processTree) prepare(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
}
func (tree *processTree) attach(cmd *exec.Cmd) error { return nil }
func (tree *processTree) close()                     {}
func (tree *processTree) stop(cmd *exec.Cmd) {
	if cmd.Process == nil {
		return
	}
	syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	cmd.Process.Kill()
}
