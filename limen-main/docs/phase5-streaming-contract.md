# Phase 5 — Streaming-Vertrag

Phase 5 schaltet `stream=true` als eigenen Pfad frei. Der Vertrag auf
dieser Seite ist die einzige Wahrheit für SSE/Pseudo-Streaming; bei
Widerspruch zwischen Code und diesem Dokument gilt das Dokument.

Verwandt: [`ARCHITECTURE.md` §Phase 5](../ARCHITECTURE.md#phase-5--streaming-und-äußere-kompatibilitätsverträge),
[`docs/phase1-reset-gate.md`](./phase1-reset-gate.md),
[`tests/integration/test_phase5_streaming_contract.py`](../tests/integration/test_phase5_streaming_contract.py).

## 1. Geltungsbereich

- Eingehender Wire-Pfad: `POST /v1/chat/completions` mit `stream: true`.
- Nicht betroffen: jede Anfrage mit `stream: false` (oder fehlendem Feld)
  bleibt unter dem bestehenden MVP-Vertrag. Konfiguration und Provider-
  Registry sind nicht betroffen.
- Nicht betroffen: Tools, Multimodalität, Function Calling — diese sind
  eigene Kompatibilitätsverträge und werden in Phase 5 nicht mit
  implementiert.

## 2. Separate Response-Shape

| Eigenschaft | Wert |
|---|---|
| HTTP-Status | `200 OK` während ein erfolgreicher Stream läuft |
| `Content-Type` | `text/event-stream; charset=utf-8` |
| `Cache-Control` | `no-cache, no-transform` |
| `Connection` | `keep-alive` |
| `X-Accel-Buffering` | `no` (damit NGINX nicht puffert) |
| Format | Server-Sent Events (`data:`-Records, `\\n\\n`-Trenner) |

Jedes Event ist genau ein einzeiliger JSON-Datensatz gefolgt von einer
Leerzeile (`\\n\\n`). Mehrzeilige Daten werden nicht verwendet.

### 2.1 Stream-Chunk-Shape

Pro Chunk-Event:

```json
{
  "id": "chatcmpl-<request_id>",
  "object": "chat.completion.chunk",
  "created": 1735689600,
  "model": "<resolved model>",
  "choices": [
    {
      "index": 0,
      "delta": { "role": "assistant" | "content": "..." },
      "finish_reason": null | "stop" | "length" | "tool_calls"
    }
  ]
}
```

- `object` ist exakt `chat.completion.chunk`, niemals `chat.completion`.
- `delta.role` erscheint nur im ersten Chunk.
- `delta.content` erscheint in 0..n Folgeschritten.
- `finish_reason != null` erscheint nur im letzten regulären Chunk.
- `usage`-Block: optional, exakt einmal vor `[DONE]`, falls der
  upstream Provider Token-Counts meldet. Niemals in regulären Chunks.

### 2.2 Terminator-Events

| Marker | Bedeutung |
|---|---|
| `data: [DONE]\\n\\n` | Erfolgreiches Ende des Streams |
| `data: {"error":{...}}\\n\\n` gefolgt von `data: [DONE]\\n\\n` | Mid-Stream-Fehler, kein automatischer Retry |

`[DONE]` erscheint niemals vor mindestens einem regulären Chunk oder
einem Mid-Stream-Fehler-Chunk. Vor Erreichen des ersten Upstream-Chunks
ist der Fehlerpfad der Phase 1: `application/json` mit
`{"error":{...}}` und passendem Status-Code.

## 3. No-Retry-nach-erstem-Chunk-Regel

Definition **erster Chunk**: das früheste SSE-Event, das LIMEN an den
Client gesendet hat. Das Reset-Gate definiert dies als „die erste
`send()`-Operation, die einen vollständigen SSE-Record inklusive
Trenner-`\\n\\n` an das Client-Socket schreibt".

| Phase | Verhalten |
|---|---|
| Pre-Stream | gleicher Key-Pool-/Rotation-Vertrag wie in Phase 1 |
| Nach erstem Chunk | **keine** Key-Rotation, **keine** Cohorte wechseln, **keine** Fallback-Provider |

Begründung: ein partiell gestreamter Response-Inhalt kann nicht
sicher wiederholt werden. Der Client hat bereits Tokens empfangen.
Ein transparent ersetztes Ergebnis verstößt gegen das was er gelesen
hat.

Error-Pfad nach erstem Chunk:

1. Upstream-Failure wird nicht retryt.
2. LIMEN sendet ein Mid-Stream-`error`-Event (Shape identisch zur
   bestehenden `{"error":{"message","type","param?","code?"}}`).
3. Direkt danach `data: [DONE]\\n\\n`.
4. LIMEN setzt — wenn der Chunk das letzte Event war — `X-LIMEN-Failure`
   auf den zuletzt berichteten Failure-Type. `Retry-After` wird ab
   diesem Zeitpunkt **nicht** mehr als Response-Header gesetzt.
5. Audit-Eintrag wird geschrieben mit `stream_partial=true`.

Error-Pfad vor erstem Chunk:

1. Verhalten exakt wie Phase-1-Vertrag: passender HTTP-Status,
   `application/json`-Envelope, kein SSE-`Content-Type`.

## 4. Header-Policy

| Header | Wert | Wer |
|---|---|---|
| `Content-Type` | `text/event-stream; charset=utf-8` | LIMEN |
| `Cache-Control` | `no-cache, no-transform` | LIMEN |
| `Connection` | `keep-alive` | LIMEN |
| `X-Accel-Buffering` | `no` | LIMEN |
| `X-Proxy-Request-Id` | `<uuid-hex>` | LIMEN |
| `X-Proxy-Correlation-Id` | `<uuid-hex>` | LIMEN |
| `X-LIMEN-Failure` | nur bei stream-Finalisierung, last-write-wins | LIMEN |
| Verboten | `Set-Cookie`, `X-Provider-*` aus Upstream | LIMEN filtert aktiv |

Upstream-Header werden ausschließlich für Steuerung (`X-Request-Id`
falls vorhanden) ausgewertet, niemals an den Client durchgereicht.

## 5. Client-Disconnect-Semantik

- LIMEN muss den Upstream-Stream beenden, sobald der Client disconnectet.
  Dies erfolgt über `async with http_client.stream(...)` oder eine
  explizite Task-Cancellation.
- Kein leeres `[DONE]` nach Disconnect: der Stream endet sofort ohne
  terminierende Events.
- LIMEN darf keine Retry-Logik nach Disconnect triggern.
- Audit-Eintrag: `client_disconnected=true`, `stream_partial=true`
  falls kein reguläres Ende.

## 6. Backpressure

- LIMEN puffert **keine** Tokens für später — jeder Chunk wird sofort
  an den Client weitergereicht.
- `httpx.AsyncClient` Read-Timeout für Streaming wird vom
  Non-Streaming-Timeout getrennt konfiguriert
  (`timeouts.stream_read_seconds`). Default: identisch zu `read_seconds`.
- Bei eingehendem `httpx.RemoteProtocolError` oder leerem
  `httpx.ReadError` erfolgt der Mid-Stream-Error-Pfad (§3).

## 7. Verbotene Pfade in Phase 5

- Synchrone Adapter-Calls (`requests` statt `httpx`).
- Buffern und Replay auf limen-internen Puffern.
- SSE-Re-Mapping von Nicht-Stream-Providern (kein Fake-Streaming).
- Tools / Multimodalität / Function Calling — separate Kompatibilitäts-
  schicht, eigener Vertrag.
- `Retry-After` Response-Header nach erstem Chunk.

## 8. Reset-Gate

Phase 5 gilt als reset, **wenn alle Tests in
`tests/integration/test_phase5_streaming_contract.py` grün** sind und:

1. `tests/integration/test_phase1_dispatcher.py` weiter grün (kein
   Backslide im MVP-Pfad).
2. `docs/phase1-reset-gate.md` weiterhin erfüllt.
3. Kein neues Sync-Call in `src/limen/` ohne expliziten Marker.
4. Der `pytest` Lauf meldet keine `StarletteDeprecationWarning` aus dem
   Streaming-Pfad (Testclient-Warnung bleibt separat dokumentiert).

## 9. Test-Mapping

Jeder Vertragspunkt hat genau einen Test. Das Test-Gerüst ist unter
`tests/integration/test_phase5_streaming_contract.py` abgelegt; die
Tests sind bis Phase-5-Implementierung per `@pytest.mark.skip`
markiert. Sobald die Implementierung steht, werden sie ohne weitere
Änderungen am Testfile aktiv.

| Vertragspunkt | Testname |
|---|---|
| §2 Content-Type | `test_streaming_response_uses_event_stream_content_type` |
| §2 Object-Shape | `test_streaming_emits_only_chat_completion_chunk_objects` |
| §2 Sequenz | `test_streaming_emits_role_then_content_then_done` |
| §2 Usage | `test_streaming_emits_usage_chunk_once_before_done` |
| §3 Pre-Stream-Error | `test_streaming_pre_first_chunk_error_uses_json_envelope` |
| §3 No-Retry | `test_streaming_does_not_retry_after_first_chunk` |
| §3 Mid-Stream-Error | `test_streaming_emits_error_chunk_then_done_marker` |
| §4 Header-Policy | `test_streaming_does_not_leak_upstream_or_set_cookie_headers` |
| §5 Client-Disconnect | `test_streaming_terminates_upstream_on_client_disconnect` |
| §6 Backpressure | `test_streaming_forwards_chunks_without_internal_buffering` |
| §7 Verbot | `test_streaming_rejects_request_with_max_tokens_zero_pre_first_chunk` |
| §8 Reset-Gate | `test_streaming_request_with_repeated_meta_chunks_is_idempotent` |

Diese Tests sind stub-frei: sie operieren auf realer `httpx.MockTransport`,
einem echten `FastAPI StreamingResponse` und einem SSE-Parser; das
einzige was sie heute tun ist `pytest.mark.skip` mit klarer Begründung.
