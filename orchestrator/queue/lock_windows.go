//go:build windows

package queue

import (
	"os"
	"syscall"
	"unsafe"
)

var lockFileEx = syscall.NewLazyDLL("kernel32.dll").NewProc("LockFileEx")

func lockQueueFile(file *os.File) error {
	var overlapped syscall.Overlapped
	const exclusiveAndImmediate = 0x00000002 | 0x00000001
	ok, _, err := lockFileEx.Call(file.Fd(), exclusiveAndImmediate, 0, 1, 0,
		uintptr(unsafe.Pointer(&overlapped)))
	if ok == 0 {
		return err
	}
	return nil
}
