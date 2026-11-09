# Campaign objectives

A campaign can give the player optional goals in its YAML file, under the
`objectives:` key (campaign format 10.10). Objectives never decide how the
campaign ends: it is still won by taking every enemy base and lost by losing
every friendly one. A met objective grants its reward. A missed one costs
nothing.

The objectives are read once, when the campaign is generated, and kept in the
save. Changing the YAML file does not change a campaign already started. An
inverted campaign (the player on the red side) has no objectives.

The player sees them in **Campaign → Objectives** (where **Show on map**
centres the map on what is left of one), in the top bar while the campaign has
any, and on the map: the **Objectives** layer rings each base or ground object
still to take, destroy or keep. A package whose target is one of them, or a
front line next to one of their bases, carries an **Objective** badge in the
planner. Each one met or missed is announced in the debriefing
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
  - title: Blind the Syrian air defences on the Golan
    destroy:
      category: iads
    by_turn: 6
    reward:
      enemy_income: 40
      enemy_income_turns: 6
  - title: Shut down the Qiryat Plant
    destroy: Qiryat Plant
    reward:
      enemy_budget: 400
  - title: Keep the Golan South radar on the air
    survive: Golan North-119
    until_turn: 15
    reward:
      income: 20
```

## On the front line

An objective targets the front, where the fight is when the campaign starts:

- a base on the front line, facing an enemy base;
- a ground object of such a base.

A carrier or another fleet counts as on the front: it sails to the fight. An
objective behind the front (a deep base, a factory in the enemy capital) is
skipped and logged. A category without `at` counts only the sites of the
bases on the front line ("Destroy the enemy IADS near the front").

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
player's hands, a target behind the front, no target left...) is skipped and
logged. The rest of the
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

The player decides what the rewards are worth, in **Settings → Campaign
Management → Campaign Objectives**, at any time of the campaign. A campaign can
set them in its `settings:` section too.

| Setting | Default | Effect |
| --- | --- | --- |
| Objective rewards | on | Off: no reward at all. The objectives stay as goals, and the income bonuses already granted stop. |
| Objective reward scale | 1.0 | Multiplies what the campaign promises, before the caps. |
| Objectives grant budget / income / aircraft and pilots | on | Turns one kind of reward off. Income off also stops the bonuses already granted. |
| Objectives cut the enemy budget and income | on | Same for the enemy cuts. |
| Objective budget cap | 2 turns | A budget, or a budget cut, is at most this many turns of that side's income. A cut never takes the enemy budget below zero. |
| Objective income cap | 25 % | An income bonus, or cut, is at most this share of that side's income when the objective is met. |
| Objective total income cap | 50 % | All the bonuses (or cuts) paid in one turn are at most this share. |
| Objective reinforcements cap | 4 | Aircraft, and pilots, per objective. The aircraft must also fit in the squadron's size and its base's parking. |

The player is told what was actually granted. The Objectives screen shows,
for each objective in progress, what the campaign promises and what it would
grant today under these settings.
