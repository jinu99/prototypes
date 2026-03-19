package main

import (
	"bufio"
	"flag"
	"log"
	"os"

	"indie-prod-monitor/alert"
	"indie-prod-monitor/engine"
	"indie-prod-monitor/server"
	"indie-prod-monitor/store"
)

func main() {
	var (
		dbPath     = flag.String("db", "monitor.db", "SQLite database path")
		listenAddr = flag.String("addr", ":9111", "HTTP listen address")
		webhookURL = flag.String("webhook", "", "Webhook URL for alerts (Slack/Discord/ntfy)")
		threshold  = flag.Int("threshold", 10, "Simhash Hamming distance threshold for clustering")
		minLevel   = flag.String("level", "warn", "Minimum log level to process: debug, info, warn, error, fatal")
	)
	flag.Parse()

	// Initialize store
	s, err := store.New(*dbPath)
	if err != nil {
		log.Fatalf("failed to init store: %v", err)
	}
	defer s.Close()

	// Initialize alerter
	var alerter alert.Alerter
	if *webhookURL != "" {
		alerter = &alert.MultiAlerter{
			Alerters: []alert.Alerter{
				&alert.StdoutAlerter{},
				alert.NewWebhookAlerter(*webhookURL),
			},
		}
	} else {
		alerter = &alert.StdoutAlerter{}
	}

	// Initialize engine
	eng := engine.New(s, alerter)
	eng.Threshold = *threshold
	eng.MinLevel = *minLevel

	// Start background monitors
	stop := make(chan struct{})
	defer close(stop)
	go eng.RunHealthChecks(stop)
	go eng.RunHeartbeatChecker(stop)

	// Start HTTP server in background
	srv := server.New(eng, s, *listenAddr)
	go func() {
		if err := srv.Start(); err != nil {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	// Check if stdin is a pipe
	stat, _ := os.Stdin.Stat()
	if (stat.Mode() & os.ModeCharDevice) == 0 {
		// stdin is a pipe — read log lines
		log.Println("reading from stdin pipe...")
		scanner := bufio.NewScanner(os.Stdin)
		// Increase buffer for long log lines
		scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
		for scanner.Scan() {
			eng.ProcessLog(scanner.Text())
		}
		if err := scanner.Err(); err != nil {
			log.Printf("stdin read error: %v", err)
		}
		log.Println("stdin closed, server still running")
	} else {
		log.Println("no stdin pipe detected, running in server-only mode")
	}

	// Block forever (server keeps running)
	select {}
}
