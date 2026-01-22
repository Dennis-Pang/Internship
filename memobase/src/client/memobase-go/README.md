# MemoBase Go Client

Go 1.22+ SDK for the MemoBase API.

## Install
```bash
go get github.com/memodb-io/memobase/src/client/memobase-go
```

## Quick Example
```go
import (
    "github.com/google/uuid"
    "github.com/memodb-io/memobase/src/client/memobase-go/core"
    "github.com/memodb-io/memobase/src/client/memobase-go/blob"
)

// Create client (uses MEMOBASE_API_KEY if key is empty)
client, _ := core.NewMemoBaseClient("YOUR_PROJECT_URL", "")

// Create/get a user
userID := uuid.NewString()
user, _ := client.GetOrCreateUser(userID)

// Insert a chat blob
blobID, _ := user.Insert(&blob.ChatBlob{
    BaseBlob: blob.BaseBlob{Type: blob.ChatType},
    Messages: []blob.OpenAICompatibleMessage{
        {Role: "user", Content: "Hello, I am Jinjia!"},
        {Role: "assistant", Content: "Hi there! How can I help you today?"},
    },
})

// Fetch data
chatBlob, _ := user.Get(blobID)
user.Flush(blob.ChatType)          // refresh profiles
profiles, _ := user.Profile()      // list profiles

// Cleanup
_ = client.DeleteUser(userID)
```

Supported blob types: `blob.ChatType`. See `examples/main.go` for a fuller walk-through.
