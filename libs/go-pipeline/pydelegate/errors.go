package pydelegate

import "fmt"

func ErrNotConfigured(jobType string) error {
	return fmt.Errorf("no handler for job_type=%s and PYTHON_WORKER_ROOT not set", jobType)
}
