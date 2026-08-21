# Finality and reorg policy

## Purpose

Этот документ определяет, как ChainPulse работает с состояниями
`latest`, `safe`, `finalized`, обнаруживает реорганизации Ethereum
и повторно обрабатывает заменённые блоки.

## Terms

### Latest

`latest` — последний блок, который Ethereum node в данный момент считает
вершиной canonical chain.

Это наиболее свежие данные, но такой блок ещё может быть заменён в результате
reorg.

ChainPulse использует `latest` для:

- измерения задержки ingestion;
- мониторинга текущей высоты сети;
- обнаружения новых блоков.

В MVP данные `latest` не используются как окончательно подтверждённые
аналитические данные.

### Safe

`safe` — блок, который consensus client считает безопасной частью canonical
chain.

Вероятность его замены значительно ниже, чем у `latest`, но он ещё не имеет
такой же гарантии, как `finalized`.

ChainPulse использует `safe` для:

- мониторинга продвижения цепочки;
- диагностики задержки между latest и finalized;
- дополнительной проверки состояния сети.

### Finalized

`finalized` — блок, который получил crypto-economic finality.

Обычная реорганизация не должна удалять finalized-блок. Его откат потребовал
бы нарушения консенсуса и потери значительной части застейканного ETH.

В MVP `finalized` является основной границей надёжной обработки.

ChainPulse:

- выполняет обычный backfill только до finalized head;
- публикует в основной streaming pipeline finalized-блоки;
- фиксирует checkpoint только после успешной обработки finalized-блока;
- не использует фиксированное число подтверждений вместо тега `finalized`.

### Pending

`pending` относится к транзакциям, которые ещё не включены в блок.

Pending-транзакции не входят в MVP ChainPulse.

## Block lifecycle

Наблюдаемый блок может проходить состояния:

```text
latest → safe → finalized
```

Пока блок не finalized, он также может перестать быть частью canonical chain:

```text
latest → orphaned
safe   → orphaned
```

Для обычной работы ChainPulse finalized-блок не должен переходить в
`orphaned`.

## Canonical chain

Canonical chain — цепочка блоков, которую Ethereum node в данный момент считает
основной.

Для каждого `block_number` в canonical chain существует только один актуальный
`block_hash`.

При этом raw-слой может содержать несколько наблюдавшихся блоков с одинаковым
`block_number`, но разными `block_hash`.

Пример:

| block_number | block_hash | is_canonical |
| ---: | --- | --- |
| 100 | `0xAAA` | false |
| 100 | `0xBBB` | true |

Блок `0xAAA` не удаляется из raw history. Он сохраняется как ранее
наблюдавшаяся версия блока.

## Canonical metadata

Для наблюдаемых версий Ethereum-сущностей ChainPulse хранит служебные поля:

| Field | Type | Nullable | Description |
| --- | --- | ---: | --- |
| `is_canonical` | boolean | no | Принадлежит ли версия актуальной цепочке |
| `finality_status` | string | no | `latest`, `safe`, `finalized` или `orphaned` |
| `canonical_checked_at` | UTC timestamp | no | Время последней проверки |
| `orphaned_at` | UTC timestamp | yes | Когда версия перестала быть canonical |
| `reorg_id` | UUID | yes | Идентификатор обнаруженного reorg |

Эти поля создаются нашей платформой и не являются частью исходного Ethereum
JSON-RPC payload.

`is_canonical` — изменяемое служебное состояние. Сам исходный raw payload
остаётся неизменным.

Статус блока распространяется на связанные сущности:

- transactions;
- receipts;
- logs;
- derived token transfers.

Связанные записи обновляются по `block_hash`, а не только по `block_number`.

## Reorg definition

Reorg происходит, когда ранее наблюдавшаяся часть canonical chain заменяется
другой веткой.

Пример первоначальной цепочки:

```text
98:A → 99:B → 100:C → 101:D
```

После reorg:

```text
98:A → 99:B → 100:X → 101:Y
```

Общим предком является блок `99:B`.

Блоки `100:C` и `101:D` становятся orphaned.

Блоки `100:X` и `101:Y` становятся новой canonical chain.

## Reorg detection

При последовательной загрузке каждый новый блок должен ссылаться на предыдущий:

```text
current_block.parentHash == previous_block.hash
```

Если условие не выполняется, возможен reorg или разрыв загруженного диапазона.

ChainPulse также сравнивает для checkpoint:

- сохранённый `block_number`;
- сохранённый `block_hash`;
- актуальный `block_hash`, полученный от JSON-RPC для этой высоты.

Одинакового номера блока недостаточно. На одной высоте могут наблюдаться разные
версии блока.

## Reorg handling algorithm

При обнаружении замены ещё не finalized-блока ChainPulse выполняет следующие
действия.

1. Останавливает продвижение checkpoint.

2. Находит последний общий блок сохранённой и актуальной цепочки.

3. Создаёт уникальный `reorg_id`.

4. Для старых блоков после общего предка устанавливает:

```text
is_canonical = false
finality_status = "orphaned"
orphaned_at = current UTC time
reorg_id = detected reorg ID
```

5. По `block_hash` помечает как не canonical связанные:

- transactions;
- receipts;
- logs;
- token transfers.

6. Откатывает checkpoint до последнего общего предка.

7. Повторно получает блоки новой ветки начиная с:

```text
common_ancestor_number + 1
```

8. Вставляет новые версии блоков и связанных сущностей.

9. Устанавливает для новой ветки:

```text
is_canonical = true
```

10. После успешной записи всех сущностей снова продвигает checkpoint.

Raw-строки старой ветки физически не удаляются.

## Checkpoint contract

Checkpoint должен содержать минимум:

| Field | Description |
| --- | --- |
| `pipeline_name` | Название pipeline |
| `chain_id` | Ethereum chain ID |
| `block_number` | Последний полностью обработанный блок |
| `block_hash` | Хэш последнего полностью обработанного блока |
| `finality_status` | Уровень finality checkpoint |
| `updated_at` | Время обновления |
| `ingestion_run_id` | Запуск, обновивший checkpoint |

Checkpoint по одному `block_number` небезопасен, потому что блок на этой высоте
может быть заменён другим блоком.

Checkpoint обновляется только после того, как:

- блок записан;
- transactions записаны;
- receipts и logs записаны;
- целевое хранилище подтвердило операцию;
- проверки целостности завершились успешно.

## Idempotent reprocessing

Повторная обработка одного диапазона не должна создавать логические дубликаты.

Raw version keys:

| Entity | Raw version key |
| --- | --- |
| Block | `block_hash` |
| Transaction | `block_hash + transaction_hash` |
| Receipt | `block_hash + transaction_hash` |
| Log | `block_hash + log_index` |
| Token transfer | `block_hash + log_index` |

Если raw version key уже существует, повторная обработка должна быть
идемпотентной.

При этом одна logical entity может иметь несколько raw-версий, если она была
наблюдаема в разных ветках цепочки.

## Startup verification

При запуске ingestion ChainPulse не должен сразу продолжать после сохранённого
номера блока.

Сначала он должен:

1. прочитать checkpoint;
2. запросить у JSON-RPC блок с этим `block_number`;
3. сравнить полученный `block_hash` с checkpoint;
4. продолжить обработку только при совпадении;
5. при несовпадении запустить процедуру поиска общего предка.

## Finalized block mismatch

Несовпадение уже обработанного finalized-блока считается критической
аномалией.

В таком случае ChainPulse должен:

- остановить pipeline;
- не перезаписывать данные автоматически;
- записать подробную ошибку;
- отправить alert;
- потребовать ручного расследования;
- проверить JSON-RPC provider и состояние Ethereum consensus.

Обычная автоматическая reorg-процедура применяется только к блокам, которые
ещё не считались finalized.

## Consumer rules

Consumer должен:

- использовать `event_id` или raw version key для дедупликации;
- подтверждать сообщение только после успешной записи;
- не удалять старые raw-версии;
- использовать `block_hash` при обновлении canonical-статуса;
- отделять повторную доставку RabbitMQ от blockchain reorg.

Повторная доставка RabbitMQ означает, что то же сообщение было доставлено ещё
раз.

Blockchain reorg означает, что Ethereum canonical chain действительно
изменилась.

Это разные ситуации, хотя обе требуют идемпотентной обработки.

## Query rules

Raw history может содержать canonical и orphaned версии.

Обычные аналитические запросы должны использовать условие:

```sql
WHERE is_canonical = TRUE
```

Если отчёту нужны только окончательно подтверждённые данные, дополнительно
используется:

```sql
WHERE is_canonical = TRUE
  AND finality_status = 'finalized'
```

История orphaned-блоков сохраняется для:

- аудита;
- диагностики reorg;
- тестирования восстановления;
- проверки корректности pipeline.

## MVP policy

Для первой версии ChainPulse принимаются следующие решения:

1. Ethereum Mainnet является единственной сетью.
2. Pending-транзакции не собираются.
3. Основной backfill ограничивается `finalized` head.
4. Основной streaming producer публикует finalized-блоки.
5. `latest` и `safe` используются для мониторинга высоты и задержки.
6. Raw versions не удаляются при reorg.
7. Canonical-статус связанных сущностей определяется через `block_hash`.
8. Checkpoint содержит одновременно `block_number` и `block_hash`.
9. Несовпадение finalized-блока останавливает pipeline.
10. Повторная обработка должна быть идемпотентной.

## Sources

- Ethereum JSON-RPC:
  https://ethereum.org/developers/docs/apis/json-rpc/
- Ethereum Proof-of-Stake:
  https://ethereum.org/developers/docs/consensus-mechanisms/pos/
- Ethereum Proof-of-Stake FAQ:
  https://ethereum.org/developers/docs/consensus-mechanisms/pos/faqs/
