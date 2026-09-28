//go:build windows

package main

import (
	"fmt"
	"os/exec"
	"syscall"
	"unsafe"
)

const killOnJobClose = 0x00002000
const jobObjectExtendedLimitInformation = 9

type basicLimits struct {
	PerProcessUserTimeLimit int64
	PerJobUserTimeLimit     int64
	LimitFlags              uint32
	MinimumWorkingSetSize   uintptr
	MaximumWorkingSetSize   uintptr
	ActiveProcessLimit      uint32
	Affinity                uintptr
	PriorityClass           uint32
	SchedulingClass         uint32
}

type ioCounters struct {
	ReadOperationCount  uint64
	WriteOperationCount uint64
	OtherOperationCount uint64
	ReadTransferCount   uint64
	WriteTransferCount  uint64
	OtherTransferCount  uint64
}

type extendedLimits struct {
	Basic                 basicLimits
	IO                    ioCounters
	ProcessMemoryLimit    uintptr
	JobMemoryLimit        uintptr
	PeakProcessMemoryUsed uintptr
	PeakJobMemoryUsed     uintptr
}

var kernel32 = syscall.NewLazyDLL("kernel32.dll")
var createJobObject = kernel32.NewProc("CreateJobObjectW")
var setInformationJobObject = kernel32.NewProc("SetInformationJobObject")
var assignProcessToJobObject = kernel32.NewProc("AssignProcessToJobObject")

type processTree struct{ handle syscall.Handle }

func newProcessTree() (*processTree, error) {
	raw, _, err := createJobObject.Call(0, 0)
	if raw == 0 {
		return nil, fmt.Errorf("CreateJobObject: %w", err)
	}
	tree := &processTree{handle: syscall.Handle(raw)}
	limits := extendedLimits{}
	limits.Basic.LimitFlags = killOnJobClose
	ok, _, err := setInformationJobObject.Call(raw, jobObjectExtendedLimitInformation,
		uintptr(unsafe.Pointer(&limits)), unsafe.Sizeof(limits))
	if ok == 0 {
		tree.close()
		return nil, fmt.Errorf("SetInformationJobObject: %w", err)
	}
	return tree, nil
}

func (tree *processTree) prepare(cmd *exec.Cmd) {}

func (tree *processTree) attach(cmd *exec.Cmd) error {
	if cmd.Process == nil {
		return fmt.Errorf("process not started")
	}
	const processSetQuota = 0x0100
	const processTerminate = 0x0001
	handle, err := syscall.OpenProcess(processSetQuota|processTerminate, false, uint32(cmd.Process.Pid))
	if err != nil {
		return err
	}
	defer syscall.CloseHandle(handle)
	ok, _, callErr := assignProcessToJobObject.Call(uintptr(tree.handle), uintptr(handle))
	if ok == 0 {
		return fmt.Errorf("AssignProcessToJobObject: %w", callErr)
	}
	return nil
}

func (tree *processTree) close() {
	if tree.handle != 0 {
		syscall.CloseHandle(tree.handle)
		tree.handle = 0
	}
}

func (tree *processTree) stop(cmd *exec.Cmd) {
	tree.close() // KILL_ON_JOB_CLOSE terminates all associated descendants.
	if cmd.Process != nil {
		cmd.Process.Kill()
	}
}
