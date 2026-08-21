# Raw event contract v1

## Purpose

Этот документ определяет формат сырых событий, которые ChainPulse будет
создавать из ответов Ethereum JSON-RPC и передавать между компонентами платформы.

Версия контракта: `1`.

В первой версии поддерживаются события:

- `chainpulse.raw.block`;
- `chainpulse.raw.transaction`;
- `chainpulse.raw.log`.

Каждое сообщение представляет одну сущность: один блок, одну транзакцию
или один log.

## General rules

Ethereum JSON-RPC передаёт числовые значения типа `QUANTITY` в виде
hex-строк.

Примеры:

```json
"blockNumber": "0x189b768"
"value": "0xde0b6b3a7640000"
```

ChainPulse сохраняет такие значения строками и не преобразует их в JSON
`number`. Это предотвращает потерю точности для значений `uint256`.

Хэши, адреса и бинарные данные также сохраняются как hex-строки с
префиксом `0x`.

Raw payload сохраняет названия полей Ethereum JSON-RPC в `camelCase`.
Служебные поля ChainPulse используют `snake_case`.

ChainPulse MVP обрабатывает только транзакции и logs, уже включённые в блок.
Pending-транзакции в контракт v1 не входят.

## Event envelope

Каждое событие имеет общий конверт:

```json
{
  "event_id": "0x1:block:0xabc123",
  "event_type": "chainpulse.raw.block",
  "schema_version": 1,
  "chain_id": "0x1",
  "observed_at": "2026-08-21T10:30:00Z",
  "ingestion_run_id": "25dc52d5-36b0-4a33-93f2-8cfbffbe3857",
  "source": {
    "provider": "alchemy",
    "rpc_method": "eth_getBlockByNumber"
  },
  "payload": {}
}
```

| Field | Type | Required | Nullable | Description |
| --- | --- | ---: | ---: | --- |
| `event_id` | string | yes | no | Детерминированный идентификатор события для дедупликации |
| `event_type` | string | yes | no | Тип сущности и события |
| `schema_version` | integer | yes | no | Версия контракта |
| `chain_id` | hex string | yes | no | Идентификатор сети; Ethereum Mainnet — `0x1` |
| `observed_at` | RFC 3339 UTC string | yes | no | Время получения данных платформой |
| `ingestion_run_id` | UUID string | yes | no | Идентификатор запуска ingestion |
| `source.provider` | string | yes | no | JSON-RPC provider |
| `source.rpc_method` | string | yes | no | Метод, которым получены данные |
| `payload` | object | yes | no | Данные конкретной Ethereum-сущности |

`observed_at` создаётся нашей платформой и не является временем блока.

`event_id` детерминированный: при повторной обработке одной сущности
должно получаться то же значение.

`ingestion_run_id`, наоборот, различается между отдельными запусками ingestion.

## Block event

Тип события:

```text
chainpulse.raw.block
```

Один block event представляет одну наблюдаемую версию Ethereum-блока.

| Payload field | Type | Required | Nullable | Description |
| --- | --- | ---: | ---: | --- |
| `number` | hex quantity string | yes | no | Номер блока |
| `hash` | 32-byte hex string | yes | no | Хэш блока |
| `parentHash` | 32-byte hex string | yes | no | Хэш родительского блока |
| `timestamp` | hex quantity string | yes | no | Unix timestamp блока |
| `miner` | address hex string | yes | no | Адрес получателя вознаграждения |
| `gasLimit` | hex quantity string | yes | no | Лимит газа блока |
| `gasUsed` | hex quantity string | yes | no | Использованный газ |
| `transactionsRoot` | 32-byte hex string | yes | no | Корень дерева транзакций |
| `receiptsRoot` | 32-byte hex string | yes | no | Корень дерева receipts |
| `stateRoot` | 32-byte hex string | yes | no | Корень состояния |
| `logsBloom` | hex data string | yes | no | Bloom filter для logs |
| `transactions` | array of transaction hashes | yes | no | Хэши транзакций блока |
| `baseFeePerGas` | hex quantity string | no | no | Base fee после EIP-1559 |
| `blobGasUsed` | hex quantity string | no | no | Использованный blob gas |
| `excessBlobGas` | hex quantity string | no | no | Excess blob gas |

Поля `baseFeePerGas`, `blobGasUsed` и `excessBlobGas` optional, потому что
их нет у блоков, созданных до соответствующих обновлений Ethereum.

Хотя `eth_getBlockByNumber` может вернуть полные объекты транзакций,
block event хранит в `transactions` только их хэши. Каждая полная
транзакция публикуется отдельным transaction event.

Формирование ключа:

```text
event_id = chain_id + ":block:" + block_hash
```

Пример:

```text
0x1:block:0xabc123
```

## Transaction event

Тип события:

```text
chainpulse.raw.transaction
```

Один transaction event представляет одно включение подписанной транзакции
в конкретный блок.

| Payload field | Type | Required | Nullable | Description |
| --- | --- | ---: | ---: | --- |
| `hash` | 32-byte hex string | yes | no | Хэш транзакции |
| `blockHash` | 32-byte hex string | yes | no | Хэш блока включения |
| `blockNumber` | hex quantity string | yes | no | Номер блока |
| `transactionIndex` | hex quantity string | yes | no | Позиция транзакции в блоке |
| `from` | address hex string | yes | no | Адрес отправителя |
| `to` | address hex string | yes | yes | Адрес назначения |
| `nonce` | hex quantity string | yes | no | Nonce отправителя |
| `value` | hex quantity string | yes | no | Количество ETH в wei |
| `gas` | hex quantity string | yes | no | Предоставленный gas limit |
| `gasPrice` | hex quantity string | yes | no | Gas price из RPC-объекта |
| `input` | hex data string | yes | no | Входные данные транзакции |
| `type` | hex quantity string | yes | no | Тип транзакции |
| `v` | hex quantity string | yes | no | Компонент подписи |
| `r` | hex quantity string | yes | no | Компонент подписи |
| `s` | hex quantity string | yes | no | Компонент подписи |
| `chainId` | hex quantity string | no | no | Chain ID подписанной транзакции |
| `maxFeePerGas` | hex quantity string | no | no | Максимальная комиссия EIP-1559 |
| `maxPriorityFeePerGas` | hex quantity string | no | no | Priority fee EIP-1559 |
| `maxFeePerBlobGas` | hex quantity string | no | no | Максимальная blob gas fee |
| `blobVersionedHashes` | array of hex strings | no | no | Blob versioned hashes |
| `accessList` | array | no | no | Access list транзакции |

`to` является required, но nullable:

```json
{
  "to": null
}
```

Это происходит при транзакции создания контракта.

Fee-поля некоторых типов транзакций могут отсутствовать, поэтому они optional.

Формирование ключа:

```text
event_id =
    chain_id
    + ":transaction:"
    + block_hash
    + ":"
    + transaction_hash
```

`transaction_hash` идентифицирует подписанную транзакцию.

`block_hash` также включён в raw event ID, потому что после reorg одна
транзакция может наблюдаться в контексте другого блока.

## Log event

Тип события:

```text
chainpulse.raw.log
```

Один log event представляет один log, созданный выполнением транзакции.

| Payload field | Type | Required | Nullable | Description |
| --- | --- | ---: | ---: | --- |
| `blockHash` | 32-byte hex string | yes | no | Хэш блока |
| `blockNumber` | hex quantity string | yes | no | Номер блока |
| `transactionHash` | 32-byte hex string | yes | no | Хэш транзакции |
| `transactionIndex` | hex quantity string | yes | no | Позиция транзакции в блоке |
| `logIndex` | hex quantity string | yes | no | Позиция log внутри блока |
| `address` | address hex string | yes | no | Адрес контракта, создавшего log |
| `topics` | array of 32-byte hex strings | yes | no | Индексированные данные события |
| `data` | hex data string | yes | no | Неиндексированные данные события |
| `removed` | boolean | yes | no | Был ли log удалён из canonical chain |

Формирование ключа:

```text
event_id =
    chain_id
    + ":log:"
    + block_hash
    + ":"
    + log_index
```

`transactionHash` нельзя использовать как единственный ключ, потому что
одна транзакция может создать несколько logs.

## Required, nullable and optional fields

Эти понятия имеют разные значения.

### Required

Поле обязательно должно присутствовать:

```json
{
  "hash": "0xabc123"
}
```

### Nullable

Поле обязательно присутствует, но может содержать `null`:

```json
{
  "to": null
}
```

### Optional

Поле может вообще отсутствовать в JSON:

```text
baseFeePerGas
```

Например, `baseFeePerGas` отсутствует у исторических блоков до EIP-1559.

## Versioning rules

Текущая версия контракта:

```text
schema_version = 1
```

Обратно совместимыми изменениями считаются:

- добавление нового optional-поля;
- добавление нового `event_type`;
- расширение документации без изменения смысла поля.

Новая версия контракта требуется при:

- удалении существующего поля;
- переименовании поля;
- изменении типа поля;
- превращении optional-поля в required;
- изменении смысла существующего поля.

Producer не должен незаметно изменять контракт уже опубликованной версии.

Consumer должен проверять `event_type` и `schema_version` перед обработкой.

## Receipt scope

Receipt входит в общую модель данных ChainPulse, но отдельный receipt event
не входит в контракт v1 этой задачи.

Контракт `chainpulse.raw.receipt` будет добавлен перед реализацией загрузки
receipts. Это не потребует изменения существующих block, transaction и log
events.

## Sources

- Ethereum JSON-RPC:
  https://ethereum.org/developers/docs/apis/json-rpc/
- EIP-1474:
  https://eips.ethereum.org/EIPS/eip-1474
