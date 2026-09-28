package main

import (
	"flag"
	"log"
	"net"
	"net/http"
	"time"

	"rl-llm-data-agent/orchestrator/queue"
	"rl-llm-data-agent/orchestrator/service"
)

func main() {
	state := flag.String("state", "work/v5_queue/state.json", "durable queue snapshot")
	listen := flag.String("listen", "127.0.0.1:8765", "loopback listen address")
	flag.Parse()
	host, _, err := net.SplitHostPort(*listen)
	if err != nil || net.ParseIP(host) == nil || !net.ParseIP(host).IsLoopback() {
		log.Fatal("alpha coordinator must bind to a numeric loopback address")
	}
	q, err := queue.Open(*state)
	if err != nil {
		log.Fatal(err)
	}
	defer q.Close()
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	go func() {
		for now := range ticker.C {
			if lost, err := q.Reap(now); err != nil {
				log.Printf("reap: %v", err)
			} else if len(lost) != 0 {
				log.Printf("lost %d lease(s); devices quarantined until cleanup", len(lost))
			}
		}
	}()
	log.Printf("coordinator listening on %s", *listen)
	log.Fatal(http.ListenAndServe(*listen, &service.Server{Queue: q}))
}
