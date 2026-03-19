package alert

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

type AlertType string

const (
	AlertNewCluster    AlertType = "new_cluster"
	AlertHealthDown    AlertType = "health_down"
	AlertHeartbeatMiss AlertType = "heartbeat_miss"
)

type Alert struct {
	Type    AlertType `json:"type"`
	Title   string    `json:"title"`
	Message string    `json:"message"`
	Time    time.Time `json:"time"`
}

type Alerter interface {
	Send(alert Alert) error
}

// StdoutAlerter prints alerts to stdout.
type StdoutAlerter struct{}

func (s *StdoutAlerter) Send(a Alert) error {
	log.Printf("[ALERT:%s] %s — %s", a.Type, a.Title, a.Message)
	return nil
}

// WebhookAlerter sends alerts to a webhook URL (Slack/Discord/ntfy compatible).
type WebhookAlerter struct {
	URL    string
	Client *http.Client
}

func NewWebhookAlerter(url string) *WebhookAlerter {
	return &WebhookAlerter{
		URL:    url,
		Client: &http.Client{Timeout: 10 * time.Second},
	}
}

func (w *WebhookAlerter) Send(a Alert) error {
	payload := map[string]string{
		"text":    fmt.Sprintf("[%s] %s\n%s", a.Type, a.Title, a.Message),
		"title":   a.Title,
		"message": a.Message,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	resp, err := w.Client.Post(w.URL, "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("webhook post: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("webhook returned %d", resp.StatusCode)
	}
	return nil
}

// MultiAlerter sends to multiple alerters.
type MultiAlerter struct {
	Alerters []Alerter
}

func (m *MultiAlerter) Send(a Alert) error {
	var lastErr error
	for _, al := range m.Alerters {
		if err := al.Send(a); err != nil {
			log.Printf("alert send error: %v", err)
			lastErr = err
		}
	}
	return lastErr
}
