# Ethereum data model

## Scope

В MVP рассматриваются blocks, transactions, receipts, logs,
ERC-20 token transfers и addresses.

## Entities

| Entity | Grain | Entity key | Raw version key | Parent/relations | JSON-RPC source |
| --- | --- | --- | --- | --- | --- |
| Block | Одна наблюдаемая версия блока | block_hash | block_hash | Один block содержит много transactions; parent_hash ссылается на предыдущий block | eth_getBlockByNumber |
| Transaction | Одно включение подписанной транзакции в блок | transaction_hash | block_hash + transaction_hash | Один block содержит много transactions | eth_getBlockByNumber |
| Receipt | Один результат выполнения транзакции в конкретном блоке | transaction_hash | block_hash + transaction_hash | Одна transaction inclusion имеет один receipt | eth_getTransactionReceipt |
| Log | Один log, созданный выполнением транзакции | Для canonical-слоя transaction_hash + log_index | block_hash + log_index | Один receipt содержит ноль или много logs | eth_getTransactionReceipt или eth_getLogs |
| ERC-20 token transfer | Один декодированный ERC-20 Transfer log | Для canonical-слоя transaction_hash + log_index | block_hash + log_index | Один подходящий log создаёт один decoded transfer | Производная сущность из log |
| Address | Один нормализованный Ethereum address | address | address | Адрес встречается в transactions, logs и token transfers | Производная сущность; при необходимости eth_getCode |

## Important distinctions

### Transaction vs receipt

Транзакция — подписанная инструкция, отправленная в Ethereum: перевод ETH, вызов контракта или создание контракта.

Receipt — результат выполнения транзакции в конкретном блоке. Он содержит статус выполнения, использованный газ, адрес созданного контракта и logs. Pending-транзакция ещё не имеет receipt.

### ETH transfer vs ERC-20 transfer

ETH transfer изменяет нативные ETH-балансы Ethereum. В рамках MVP прямой перевод определяется через transaction.value.

ERC-20 transfer изменяет балансы внутри storage токен-контракта и создаёт Transfer log. Такой перевод может быть вызван напрямую через функцию transfer или косвенно другим смарт-контрактом.

Количество ERC-20 токенов берётся из Transfer log, а не из transaction.value.

### Block number vs block hash

block_number обозначает высоту блока. При reorg на одной высоте могут быть последовательно замечены разные блоки.

block_hash идентифицирует конкретную версию блока. Старый блок сохраняет свой номер и хеш, но перестаёт быть canonical. Новый блок получает тот же block_number, но другой block_hash.

### Raw entity vs derived entity

Raw entity получается непосредственно из Ethereum JSON-RPC с минимальными изменениями. К raw-сущностям относятся blocks, transactions, receipts и logs.

Derived entity создаётся нашей платформой из raw-данных. ERC-20 token transfer декодируется из Transfer log, а address dimension собирается из адресов, найденных в разных raw-сущностях.

## Reorg considerations

При reorg старый блок заменяется другим блоком на той же высоте. Старый и новый блоки имеют разные block_hash.

Raw-слой должен сохранять наблюдаемые версии по block_hash. Старые blocks, transaction inclusions, receipts, logs и token transfers помечаются как не canonical, а данные нового блока загружаются отдельно.

Canonical-модели должны показывать только сущности из актуальной цепочки. Checkpoint при необходимости откатывается назад, после чего диапазон блоков обрабатывается повторно. Повторная обработка не должна создавать логические дубликаты.
