package server

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"indie-prod-monitor/engine"
	"indie-prod-monitor/store"
)

type Server struct {
	Engine *engine.Engine
	Store  *store.Store
	Addr   string
}

func New(eng *engine.Engine, s *store.Store, addr string) *Server {
	return &Server{Engine: eng, Store: s, Addr: addr}
}

func (s *Server) Start() error {
	mux := http.NewServeMux()

	// POST /ingest — receive log lines via HTTP
	mux.HandleFunc("/ingest", s.handleIngest)

	// POST /healthcheck — register a healthcheck
	mux.HandleFunc("/healthcheck", s.handleHealthCheck)

	// POST /heartbeat/{name} — register or beat a heartbeat
	mux.HandleFunc("/heartbeat/", s.handleHeartbeat)

	// GET /status — overview of clusters, healthchecks, heartbeats
	mux.HandleFunc("/status", s.handleStatus)

	log.Printf("HTTP server listening on %s", s.Addr)
	return http.ListenAndServe(s.Addr, mux)
}

func (s *Server) handleIngest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	var body struct {
		Lines []string `json:"lines"`
		Line  string   `json:"line"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}

	lines := body.Lines
	if body.Line != "" {
		lines = append(lines, body.Line)
	}

	for _, line := range lines {
		s.Engine.ProcessLog(line)
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"processed": %d}`, len(lines))
}

func (s *Server) handleHealthCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	var body struct {
		Name     string `json:"name"`
		URL      string `json:"url"`
		Interval int    `json:"interval"` // seconds
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}
	if body.Name == "" || body.URL == "" {
		http.Error(w, "name and url required", http.StatusBadRequest)
		return
	}
	if body.Interval <= 0 {
		body.Interval = 60
	}

	if err := s.Store.UpsertHealthCheck(body.Name, body.URL, body.Interval); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"registered": "%s"}`, body.Name)
}

func (s *Server) handleHeartbeat(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Path[len("/heartbeat/"):]
	if name == "" {
		http.Error(w, "name required in path", http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodPost:
		// Register or beat
		var body struct {
			Interval int `json:"interval"` // seconds, optional for registration
		}
		json.NewDecoder(r.Body).Decode(&body) // ignore error, fields optional

		if body.Interval > 0 {
			if err := s.Store.UpsertHeartbeat(name, body.Interval); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
		}

		if err := s.Store.RecordBeat(name); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"beat": "%s"}`, name)

	default:
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", http.StatusMethodNotAllowed)
		return
	}

	type statusResp struct {
		Clusters     []store.Cluster     `json:"clusters"`
		HealthChecks []store.HealthCheck  `json:"healthchecks"`
		Heartbeats   []store.Heartbeat   `json:"heartbeats"`
	}

	var resp statusResp

	// Get recent clusters (last 50)
	rows, err := s.Store.DB().Query(
		"SELECT id, hash, sample, count, first_seen, last_seen FROM clusters ORDER BY last_seen DESC LIMIT 50",
	)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var c store.Cluster
			var h int64
			rows.Scan(&c.ID, &h, &c.Sample, &c.Count, &c.FirstSeen, &c.LastSeen)
			c.Hash = uint64(h)
			resp.Clusters = append(resp.Clusters, c)
		}
	}

	resp.HealthChecks, _ = s.Store.GetAllHealthChecks()
	resp.Heartbeats, _ = s.Store.GetAllHeartbeats()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
