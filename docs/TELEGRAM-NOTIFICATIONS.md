# Notificações Telegram

Documento de decisão e guia de implantação para notificações Telegram da Máquina de Cortes.

## Decisão

Por enquanto, manter a especificação documentada aqui. A configuração ideal é feita pela página **Configurações** do frontend, não por variáveis de ambiente do bot.

O token do bot e os chats inscritos devem ficar no storage compartilhado:

```text
settings/telegram.json
```

Formato esperado:

```json
{
  "enabled": true,
  "botToken": "123456789:AA...",
  "botUsername": "meu_bot",
  "notifyOn": ["triggered", "run_error", "error", "expired"],
  "subscribers": [
    {
      "chatId": "123456789",
      "username": "usuario",
      "firstName": "Nome",
      "registeredAt": "2026-07-03T12:00:00Z"
    }
  ]
}
```

## Arquitetura

```text
scheduler/live_watch
  -> LPUSH cuts:notify
  -> Redis
  -> telegram-bot BRPOP
  -> Telegram sendMessage
```

O serviço `telegram-bot` também usa long polling para receber `/start` e registrar automaticamente o `chat_id` no blob de settings.

## Eventos Notificados

Notificar:

- `triggered`: run automática criada.
- `run_error`: match encontrado, mas falhou ao criar a run.
- `error`: erro de checagem, normalmente `yt-dlp`.
- `expired`: janela do monitor expirou sem match.

Não notificar no MVP:

- `still_live`
- `no_match`
- `waiting`
- `already_triggered`
- `low_score`
- `duplicate_video`

## Serviços

### Backend API

Endpoints desejados:

- `GET /v1/settings/telegram`
- `PUT /v1/settings/telegram`
- `POST /v1/settings/telegram/test`

Responsabilidades:

- Ler e escrever `settings/telegram.json`.
- Nunca retornar o token puro no `GET`; retornar apenas token mascarado.
- Enfileirar mensagem de teste em `cuts:notify`.

### Scheduler

Responsabilidades:

- Publicar mensagens em Redis após salvar logs do Monitor de Lives.
- Fila padrão: `cuts:notify`.

### telegram-bot

Responsabilidades:

- Ler `settings/telegram.json`.
- Fazer long polling no Telegram.
- Registrar chats via `/start`.
- Consumir `cuts:notify` via `BRPOP`.
- Deduplicar mensagens por curto período no Redis.
- Enviar mensagens com links para a run e para o Monitor de Lives.

## Variáveis de Ambiente

### telegram-bot

Obrigatórias:

- `REDIS_URL`
- `DATA_DIR` ou configuração S3 compartilhada
- `FRONTEND_URL`

Recomendadas:

- `REDIS_QUEUE_NOTIFY=cuts:notify`
- `TELEGRAM_POLL_INTERVAL_S=2`
- `NOTIFY_DEDUPE_TTL_S=300`

Se usar S3/MinIO:

- `S3_ENDPOINT`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `S3_USE_SSL`
- `S3_REGION`

### scheduler

- `REDIS_URL`
- `REDIS_QUEUE_NOTIFY=cuts:notify`
- `FRONTEND_URL` para montar links nas mensagens, se os links forem montados no scheduler.

### api

Nenhuma variável nova obrigatória além das já usadas para Redis e storage compartilhado.

## Guia de Configuração no Frontend

1. Criar um bot no Telegram com `@BotFather` usando `/newbot`.
2. Copiar o token do bot.
3. Abrir **Configurações > Notificações Telegram**.
4. Colar o token.
5. Opcionalmente preencher o `@username` do bot.
6. Salvar.
7. Abrir o bot no Telegram e enviar `/start`.
8. Conferir se o chat apareceu na lista de inscritos.
9. Usar **Enviar teste**.

Alternativa para chat manual:

1. Abrir `@userinfobot`.
2. Copiar o `chat_id`.
3. Adicionar o chat manualmente em Settings.

## Guia de Deploy

Subir um novo serviço:

```text
telegram-bot
```

Build esperado:

```text
context: backend/
dockerfile: telegram-bot/Dockerfile
```

Checklist:

1. `telegram-bot` usa o mesmo Redis da API e do scheduler.
2. `telegram-bot` usa o mesmo storage compartilhado da API.
3. `FRONTEND_URL` aponta para a URL pública do frontend.
4. Token e chats são configurados pela UI.
5. Rodar teste pelo Settings.

## Observações

- O Telegram não permite o bot iniciar conversa com usuário novo apenas pelo user ID.
- O usuário precisa enviar `/start` uma vez, ou o chat precisa ser adicionado manualmente com um chat ID válido que já possa receber mensagens do bot.
- Webhook pode substituir long polling depois, mas long polling é suficiente para o MVP.
