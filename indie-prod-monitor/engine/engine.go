package engine

import (
	"log"
	"net/http"
	"strings"
	"time"

	"indie-prod-monitor/alert"
	"indie-prod-monitor/simhash"
	"indie-prod-monitor/store"
)

const DefaultThreshold = 10 // Hamming distance threshold for "same cluster"

type Engine struct {
	Store     *store.Store
	Alerter   alert.Alerter
	Threshold int
	MinLevel  string // minimum log level to process: "debug", "info", "warn", "error", "fatal"
}

func New(s *store.Store, a alert.Alerter) *Engine {
	return &Engine{
		Store:     s,
		Alerter:   a,
		Threshold: DefaultThreshold,
		MinLevel:  "warn",
	}
}

var levelPriority = map[string]int{
	"trace": 0, "debug": 1, "info": 2, "warn": 3, "warning": 3, "error": 4, "err": 4, "fatal": 5, "panic": 5,
}

func detectLevel(line string) string {
	upper := strings.ToUpper(line)
	// Check first 100 chars for level keyword
	check := upper
	if len(check) > 100 {
		check = check[:100]
	}
	for _, lvl := range []string{"FATAL", "PANIC", "ERROR", "ERR", "WARN", "WARNING", "INFO", "DEBUG", "TRACE"} {
		if strings.Contains(check, lvl) {
			return strings.ToLower(lvl)
		}
	}
	return "info" // default: treat unknown as info
}

// ProcessLog takes a log line, computes its simhash, finds or creates a cluster,
// and alerts if it's a new cluster.
func (e *Engine) ProcessLog(line string) {
	if len(line) == 0 {
		return
	}

	// Filter by log level
	level := detectLevel(line)
	minPri, ok := levelPriority[e.MinLevel]
	if !ok {
		minPri = 3 // default to warn
	}
	if levelPriority[level] < minPri {
		return
	}

	hash := simhash.Hash(line)

	existing, err := e.Store.FindCluster(hash, e.Threshold)
	if err != nil {
		log.Printf("error finding cluster: %v", err)
		return
	}

	if existing != nil {
		if err := e.Store.IncrementCluster(existing.ID); err != nil {
			log.Printf("error incrementing cluster: %v", err)
		}
		return
	}

	// New cluster — this is a never-before-seen error pattern
	cluster, err := e.Store.InsertCluster(hash, line)
	if err != nil {
		log.Printf("error inserting cluster: %v", err)
		return
	}

	log.Printf("new cluster #%d (hash=%016x): %s", cluster.ID, cluster.Hash, truncate(line, 120))

	e.Alerter.Send(alert.Alert{
		Type:    alert.AlertNewCluster,
		Title:   "New error pattern detected",
		Message: truncate(line, 500),
		Time:    time.Now(),
	})
}

// RunHealthChecks periodically checks all registered health endpoints.
func (e *Engine) RunHealthChecks(stop <-chan struct{}) {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-stop:
			return
		case <-ticker.C:
			e.checkHealthEndpoints()
		}
	}
}

func (e *Engine) checkHealthEndpoints() {
	checks, err := e.Store.GetAllHealthChecks()
	if err != nil {
		log.Printf("error loading healthchecks: %v", err)
		return
	}

	for _, hc := range checks {
		go func(hc store.HealthCheck) {
			client := &http.Client{Timeout: 10 * time.Second}
			resp, err := client.Get(hc.URL)

			if err != nil || resp.StatusCode >= 400 {
				prevStatus := hc.Status
				e.Store.UpdateHealthCheckStatus(hc.Name, "fail", false)
				if prevStatus != "fail" {
					e.Alerter.Send(alert.Alert{
						Type:    alert.AlertHealthDown,
						Title:   "Health check failed: " + hc.Name,
						Message: hc.URL,
						Time:    time.Now(),
					})
				}
				return
			}
			resp.Body.Close()
			e.Store.UpdateHealthCheckStatus(hc.Name, "ok", true)
		}(hc)
	}
}

// RunHeartbeatChecker periodically checks if heartbeats are overdue.
func (e *Engine) RunHeartbeatChecker(stop <-chan struct{}) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-stop:
			return
		case <-ticker.C:
			e.checkHeartbeats()
		}
	}
}

func (e *Engine) checkHeartbeats() {
	beats, err := e.Store.GetAllHeartbeats()
	if err != nil {
		log.Printf("error loading heartbeats: %v", err)
		return
	}

	now := time.Now()
	for _, hb := range beats {
		if hb.LastBeat.IsZero() {
			continue // never received a beat yet, skip
		}
		deadline := hb.LastBeat.Add(time.Duration(hb.Interval) * time.Second)
		if now.After(deadline) && hb.Status != "overdue" {
			e.Store.UpdateHeartbeatStatus(hb.Name, "overdue")
			e.Alerter.Send(alert.Alert{
				Type:    alert.AlertHeartbeatMiss,
				Title:   "Heartbeat overdue: " + hb.Name,
				Message: "Last beat: " + hb.LastBeat.Format(time.RFC3339),
				Time:    now,
			})
		}
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
