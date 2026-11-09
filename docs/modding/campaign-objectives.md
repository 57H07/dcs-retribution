# Campaign objectives

A campaign can give the player optional goals in its YAML file, under the
`objectives:` key (campaign format 10.10). Objectives never decide how the
campaign ends: it is still won by taking every enemy base and lost by losing
every friendly one. A met objective grants its reward. A missed one costs
nothing.

The objectives are read once, when the campaign is generated, and kept in the
save. Changing the YAML file does not change a campaign already started. An
inverted campaign (the player on the red side) has no objectives.

The player sees them in **Campaign → Objectives**, and in the top bar while
the campaign has any. Each one met or missed is announced in the debriefing
and the info panel.

## Example

From `resources/campaigns/golan_heights_lite.yaml`:

```yaml
objectives:
  - capture: Golan North
    by_turn: 8
    reward:
      budget: 300
      income: 30
  - title: Blind the Syrian air defences
    destroy:
      category: iads
    by_turn: 12
    reward:
      enemy_income: 40
      enemy_income_turns: 6
  - destroy:
      category: factory
      at: Damascus
    reward:
      enemy_budget: 400
  - title: Keep the Ramat David radar on the air
    survive: Golan North-118
    until_turn: 15
    reward:
      income: 20
```

## Kinds

Each objective has exactly one of these keys.

| Key | Value | Met | Missed |
| --- | --- | --- | --- |
| `capture` | an enemy base | the player owns the base at the end of a turn | `by_turn` passes first |
| `hold` | a friendly base, with `until_turn` | the player still owns it at the end of `until_turn` | the base is lost before |
| `destroy` | an enemy ground object, or `{category, at}` | every target is destroyed, or its base taken | `by_turn` passes first |
| `survive` | a friendly base or ground object, with `until_turn` | it still stands at the end of `until_turn` | it is lost, sunk or destroyed before |

- **Bases** use their name in the campaign's `.miz`: the airport name, or the
  group name of a carrier, an LHA or a FOB. A carrier renamed by the faction is
  still found by its `.miz` name.
- **Ground objects** use their group name in the `.miz` (the same names as
  `ground_forces:`), not the random name the game shows.
- **Categories**: `iads` (every air defence site, early warning radar and
  IADS node on land, not the ships), or a ground object category: `aa`, `ewr`, `factory`, `ammo`,
  `fuel`, `power`, `comms`, `commandcenter`, `oil`, `derrick`, `ware`,
  `missile`, `coastal`, `armor`... Add `at: <base>` to count only the sites
  of one base.
- `by_turn` is optional. Without it, a capture or a destroy has no deadline.
- `title` is optional. Without it, the game writes one ("Capture Golan North").

A turn number is the turn the top bar shows. An objective is checked at the
end of each turn, after the mission results are applied.

An objective that cannot be read (unknown base, a base already in the
player's hands, no target left...) is skipped and logged. The rest of the
campaign loads as usual.

## Rewards

`reward:` is optional, and its keys can be combined.

| Key | Effect |
| --- | --- |
| `budget` | Added to the player's budget once. |
| `income`, `income_turns` | Added to the player's income every turn, for `income_turns` turns or until the end. |
| `aircraft`, `pilots`, `squadron` | Aircraft and pilots given to the player's squadron with that name. |
| `enemy_budget` | Taken from the enemy's budget once. |
| `enemy_income`, `enemy_income_turns` | Taken from the enemy's income every turn, for `enemy_income_turns` turns or until the end. |

Rewards are capped, so that a campaign cannot unbalance itself. The player
is told what was actually granted.

- A budget, or a budget cut, is at most **2 turns** of that side's income.
  A cut never takes the enemy budget below zero.
- An income bonus, or cut, is at most **25 %** of that side's income when the
  objective is met. All the bonuses (or cuts) paid in one turn are at most
  **50 %** of it.
- At most **4** aircraft and **4** pilots per objective. The aircraft must
  also fit in the squadron's size and its base's parking.
