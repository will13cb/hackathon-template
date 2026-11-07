# Architecture

> Keep this diagram matching what's actually deployed. `/demo-check` flags drift. GitHub renders Mermaid natively, and for slides you can paste it into https://mermaid.live and export a PNG.

```mermaid
flowchart LR
  user([User / Browser]) -->|HTTPS| web[Static frontend<br/>web/]
  web -->|POST /api/generate| api[FastAPI<br/>api/app/main.py]
  api --> llm{{llm.py<br/>LLM_PROVIDER}}

  subgraph GCP [Google Cloud]
    run[Cloud Run] -.hosts.-> api
    llm -->|vertex| gemini[Gemini on Vertex AI]
  end

  subgraph AWS [AWS]
    lambda[Lambda + Function URL<br/>Lambda Web Adapter] -.hosts.-> api
    llm -->|bedrock| bedrock[Amazon Bedrock<br/>Converse API]
  end
```

Delete the cloud you're not using, and add the project's own pieces (data stores, agents, tools) as you build them.
