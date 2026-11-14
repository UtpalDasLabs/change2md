export interface ConversionResult {
  markdown: string;
  total_chars: number;
  offset: number;
  next_offset: number | null;
  has_more: boolean;
  source_url?: string;
  file_name?: string;
}

export interface ConvertOptions {
  offset?: number;
  maxChars?: number;
}

export class Change2MDError extends Error {}

export class Change2MD {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(baseUrl = "https://change2md.vercel.app", fetcher: typeof fetch = fetch) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetcher = fetcher;
  }

  async convertUrl(url: string, options: ConvertOptions = {}): Promise<ConversionResult> {
    return this.request("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        offset: options.offset ?? 0,
        max_chars: options.maxChars ?? 500000,
      }),
    });
  }

  async convertFile(file: Blob, fileName: string, options: ConvertOptions = {}): Promise<ConversionResult> {
    const form = new FormData();
    form.append("file", file, fileName);
    form.append("offset", String(options.offset ?? 0));
    form.append("max_chars", String(options.maxChars ?? 500000));
    return this.request("/api/convert/file", { method: "POST", body: form });
  }

  private async request(path: string, init: RequestInit): Promise<ConversionResult> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, init);
    const payload = await response.json();
    if (!response.ok) throw new Change2MDError(payload.error || `HTTP ${response.status}`);
    return payload as ConversionResult;
  }
}
