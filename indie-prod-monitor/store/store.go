package store

import (
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

type Cluster struct {
	ID        int64
	Hash      uint64
	Sample    string // first log line that created this cluster
	Count     int64
	FirstSeen time.Time
	LastSeen  time.Time
}

type HealthCheck struct {
	ID       int64
	Name     string
	URL      string
	Interval int // seconds
	LastOK   time.Time
	Status   string // "ok", "fail", "unknown"
}

type Heartbeat struct {
	ID       int64
	Name     string
	Interval int // expected interval in seconds
	LastBeat time.Time
	Status   string // "ok", "overdue"
}

type Store struct {
	db *sql.DB
}

func New(dbPath string) (*Store, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	// Enable WAL mode for concurrent reads
	db.Exec("PRAGMA journal_mode=WAL")
	db.Exec("PRAGMA busy_timeout=5000")

	if err := migrate(db); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}

	return &Store{db: db}, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

// DB returns the underlying *sql.DB for advanced queries.
func (s *Store) DB() *sql.DB {
	return s.db
}

func migrate(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS clusters (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			hash INTEGER NOT NULL,
			sample TEXT NOT NULL,
			count INTEGER NOT NULL DEFAULT 1,
			first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
		CREATE INDEX IF NOT EXISTS idx_clusters_hash ON clusters(hash);

		CREATE TABLE IF NOT EXISTS healthchecks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL UNIQUE,
			url TEXT NOT NULL,
			interval_sec INTEGER NOT NULL DEFAULT 60,
			last_ok DATETIME,
			status TEXT NOT NULL DEFAULT 'unknown'
		);

		CREATE TABLE IF NOT EXISTS heartbeats (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL UNIQUE,
			interval_sec INTEGER NOT NULL DEFAULT 300,
			last_beat DATETIME,
			status TEXT NOT NULL DEFAULT 'unknown'
		);
	`)
	return err
}

// FindCluster finds a cluster with a hash close enough (within threshold).
// Returns nil if no match found.
func (s *Store) FindCluster(hash uint64, threshold int) (*Cluster, error) {
	rows, err := s.db.Query("SELECT id, hash, sample, count, first_seen, last_seen FROM clusters")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var c Cluster
		var h int64
		if err := rows.Scan(&c.ID, &h, &c.Sample, &c.Count, &c.FirstSeen, &c.LastSeen); err != nil {
			return nil, err
		}
		c.Hash = uint64(h)
		if hammingDistance(c.Hash, hash) <= threshold {
			return &c, nil
		}
	}
	return nil, rows.Err()
}

// InsertCluster creates a new cluster and returns it.
func (s *Store) InsertCluster(hash uint64, sample string) (*Cluster, error) {
	now := time.Now()
	res, err := s.db.Exec(
		"INSERT INTO clusters (hash, sample, count, first_seen, last_seen) VALUES (?, ?, 1, ?, ?)",
		int64(hash), sample, now, now,
	)
	if err != nil {
		return nil, err
	}
	id, _ := res.LastInsertId()
	return &Cluster{
		ID: id, Hash: hash, Sample: sample, Count: 1,
		FirstSeen: now, LastSeen: now,
	}, nil
}

// IncrementCluster bumps the count and last_seen for an existing cluster.
func (s *Store) IncrementCluster(id int64) error {
	_, err := s.db.Exec(
		"UPDATE clusters SET count = count + 1, last_seen = ? WHERE id = ?",
		time.Now(), id,
	)
	return err
}

// GetAllHealthChecks returns all registered healthchecks.
func (s *Store) GetAllHealthChecks() ([]HealthCheck, error) {
	rows, err := s.db.Query("SELECT id, name, url, interval_sec, last_ok, status FROM healthchecks")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var checks []HealthCheck
	for rows.Next() {
		var hc HealthCheck
		var lastOK sql.NullTime
		if err := rows.Scan(&hc.ID, &hc.Name, &hc.URL, &hc.Interval, &lastOK, &hc.Status); err != nil {
			return nil, err
		}
		if lastOK.Valid {
			hc.LastOK = lastOK.Time
		}
		checks = append(checks, hc)
	}
	return checks, rows.Err()
}

// UpsertHealthCheck creates or updates a healthcheck.
func (s *Store) UpsertHealthCheck(name, url string, intervalSec int) error {
	_, err := s.db.Exec(`
		INSERT INTO healthchecks (name, url, interval_sec) VALUES (?, ?, ?)
		ON CONFLICT(name) DO UPDATE SET url=excluded.url, interval_sec=excluded.interval_sec
	`, name, url, intervalSec)
	return err
}

// UpdateHealthCheckStatus updates the status and optionally last_ok.
func (s *Store) UpdateHealthCheckStatus(name, status string, ok bool) error {
	if ok {
		_, err := s.db.Exec(
			"UPDATE healthchecks SET status = ?, last_ok = ? WHERE name = ?",
			status, time.Now(), name,
		)
		return err
	}
	_, err := s.db.Exec("UPDATE healthchecks SET status = ? WHERE name = ?", status, name)
	return err
}

// GetAllHeartbeats returns all registered heartbeats.
func (s *Store) GetAllHeartbeats() ([]Heartbeat, error) {
	rows, err := s.db.Query("SELECT id, name, interval_sec, last_beat, status FROM heartbeats")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var beats []Heartbeat
	for rows.Next() {
		var hb Heartbeat
		var lastBeat sql.NullTime
		if err := rows.Scan(&hb.ID, &hb.Name, &hb.Interval, &lastBeat, &hb.Status); err != nil {
			return nil, err
		}
		if lastBeat.Valid {
			hb.LastBeat = lastBeat.Time
		}
		beats = append(beats, hb)
	}
	return beats, rows.Err()
}

// UpsertHeartbeat creates or updates a heartbeat config.
func (s *Store) UpsertHeartbeat(name string, intervalSec int) error {
	_, err := s.db.Exec(`
		INSERT INTO heartbeats (name, interval_sec) VALUES (?, ?)
		ON CONFLICT(name) DO UPDATE SET interval_sec=excluded.interval_sec
	`, name, intervalSec)
	return err
}

// RecordBeat records that a heartbeat was received. Auto-creates with 300s default if not exists.
func (s *Store) RecordBeat(name string) error {
	now := time.Now()
	res, err := s.db.Exec(
		"UPDATE heartbeats SET last_beat = ?, status = 'ok' WHERE name = ?",
		now, name,
	)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		_, err = s.db.Exec(
			"INSERT INTO heartbeats (name, interval_sec, last_beat, status) VALUES (?, 300, ?, 'ok')",
			name, now,
		)
	}
	return err
}

// UpdateHeartbeatStatus updates the heartbeat status.
func (s *Store) UpdateHeartbeatStatus(name, status string) error {
	_, err := s.db.Exec("UPDATE heartbeats SET status = ? WHERE name = ?", status, name)
	return err
}

func hammingDistance(a, b uint64) int {
	x := a ^ b
	count := 0
	for x != 0 {
		count++
		x &= x - 1
	}
	return count
}
