# malaysiahub-rates

「マレーシアの歩き方」で学費などをRMと日本円で併記するための、為替レート配信用リポジトリ。

- 出典：Bank Negara Malaysia（マレーシア中央銀行）Open API
  https://api.bnm.gov.my/public/exchange-rate?session=1130&quote=rm
- 更新：GitHub Actions で毎日 09:00 UTC（17:00 MYT）
- 中身は中央銀行の公表値のみ。業務データや個人情報は入れない

## 使い方

rates.json を読む。

```
https://raw.githubusercontent.com/<owner>/malaysiahub-rates/main/rates.json
```

主なフィールド

| キー | 意味 |
|---|---|
| `myr_to_jpy` | RM1あたりの円（中値換算） |
| `usd_to_myr` | USD1あたりのRM（USD建て学費の換算用） |
| `rate_date` | BNMが公表したレートの日付 |
| `stale` | true のとき取得に失敗し、前回値をそのまま置いている |
| `history` | 日次の推移（直近400件） |

## 表示のルール

- 正はRM。円は参考値として括弧で添える
- 換算に使ったレートの日付をページに必ず出す
- 「実際の送金では銀行手数料とスプレッドが乗るため、この金額どおりにはなりません」を添える
- `stale: true` のときは日付が古い旨を出す。値を推測で埋めない

## BNMの仕様メモ

- JPYは `unit: 100`（RM per 100 JPY）で返る。RM1あたりの円は `100 / 中値`
- `middle_rate` は null で返ることがあるので、buying と selling の平均を使う
- 営業日のみ公表。土日祝は前営業日の日付が返る（`rate_date` で判別できる）
