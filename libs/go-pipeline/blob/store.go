package blob

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/woragis/cuts-go-pipeline/config"
)

type Store struct {
	cfg    config.Config
	client *minio.Client
}

func New(cfg config.Config) (*Store, error) {
	s := &Store{cfg: cfg}
	if cfg.S3Endpoint == "" {
		return s, nil
	}
	client, err := minio.New(cfg.S3Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.S3AccessKey, cfg.S3SecretKey, ""),
		Secure: cfg.S3UseSSL,
		Region: cfg.S3Region,
	})
	if err != nil {
		return nil, err
	}
	s.client = client
	return s, nil
}

func (s *Store) UsesRemote() bool {
	return s.client != nil
}

func (s *Store) MaterializePrefix(ctx context.Context, prefix string) error {
	if !s.UsesRemote() {
		return nil
	}
	prefix = normPrefix(prefix)
	for obj := range s.client.ListObjects(ctx, s.cfg.S3Bucket, minio.ListObjectsOptions{Prefix: prefix, Recursive: true}) {
		if obj.Err != nil {
			return obj.Err
		}
		if err := s.materializeKey(ctx, obj.Key); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) SyncPrefixUp(ctx context.Context, prefix string) error {
	if !s.UsesRemote() {
		return nil
	}
	prefix = normPrefix(prefix)
	root := filepath.Join(s.cfg.DataDir, filepath.FromSlash(strings.TrimSuffix(prefix, "/")))
	if _, err := os.Stat(root); os.IsNotExist(err) {
		return nil
	}
	return filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		rel, err := filepath.Rel(s.cfg.DataDir, path)
		if err != nil {
			return err
		}
		key := strings.ReplaceAll(rel, "\\", "/")
		return s.uploadFile(ctx, key, path)
	})
}

func (s *Store) materializeKey(ctx context.Context, key string) error {
	local := filepath.Join(s.cfg.DataDir, filepath.FromSlash(key))
	if st, err := os.Stat(local); err == nil && st.Size() > 0 {
		return nil
	}
	obj, err := s.client.GetObject(ctx, s.cfg.S3Bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return err
	}
	defer obj.Close()
	data, err := io.ReadAll(obj)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(local), 0o755); err != nil {
		return err
	}
	return os.WriteFile(local, data, 0o644)
}

func (s *Store) uploadFile(ctx context.Context, key, localPath string) error {
	f, err := os.Open(localPath)
	if err != nil {
		return err
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return err
	}
	_, err = s.client.PutObject(ctx, s.cfg.S3Bucket, key, f, st.Size(), minio.PutObjectOptions{})
	return err
}

func normPrefix(prefix string) string {
	p := strings.TrimPrefix(strings.ReplaceAll(prefix, "\\", "/"), "/")
	if !strings.HasSuffix(p, "/") {
		p += "/"
	}
	return p
}

func RunPrefix(runID string) string {
	return fmt.Sprintf("runs/%s/", runID)
}
