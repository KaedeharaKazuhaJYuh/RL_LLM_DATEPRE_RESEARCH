//go:build !windows

package queue

import (
	"os"
	"syscall"
)

func lockQueueFile(file *os.File) error {
	return syscall.Flock(int(file.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
}
