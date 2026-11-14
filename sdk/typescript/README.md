# Change2MD TypeScript SDK

```ts
import { Change2MD } from "@utpaldaslabs/change2md";

const client = new Change2MD();
const page = await client.convertUrl("https://example.com", { maxChars: 100000 });
console.log(page.markdown);

if (page.has_more) {
  const next = await client.convertUrl("https://example.com", {
    offset: page.next_offset!,
    maxChars: 100000,
  });
  console.log(next.markdown);
}
```

For browser file inputs:

```ts
const fileInput = document.querySelector<HTMLInputElement>("input[type=file]")!;
const file = fileInput.files![0];
const result = await client.convertFile(file, file.name, { maxChars: 100000 });
```

The SDK uses the standard `fetch`, `FormData` and `Blob` APIs. It supports current browsers and JavaScript runtimes that provide them. No model-specific dependency is required.
