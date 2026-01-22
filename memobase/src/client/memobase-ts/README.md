# Memobase TypeScript/JavaScript Client

SDK for the MemoBase REST API.

## Install
```sh
npm install @memobase/memobase
# or
deno add jsr:@memobase/memobase
npx jsr add @memobase/memobase
```

## Quick Start
```js
import { MemoBaseClient, Blob, BlobType } from '@memobase/memobase';

const client = new MemoBaseClient(
  process.env.MEMOBASE_PROJECT_URL,
  process.env.MEMOBASE_API_KEY
);

const userId = await client.addUser();
const user = await client.getOrCreateUser(userId);

const blobId = await user.insert(Blob.parse({
  type: BlobType.Enum.chat,
  messages: [{ role: 'user', content: 'Hello from JS' }],
}));

await user.flush(BlobType.Enum.chat);
const profiles = await user.profile();
const context = await user.context(2000, 1000);
await client.deleteUser(userId);
```

## Support
- Discord: https://discord.gg/YdgwU4d9NB
- Email: contact@memobase.io
