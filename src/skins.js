// Market names look like "[★ ][StatTrak™ ]Weapon | Finish (Wear)". The
// watchlist picker builds them from parts so users only type the finish,
// and checks them against the names the scraper actually has data for
// (GET /api/skins), since anything else comes back with no listings.

export const WEARS = [
  'Factory New',
  'Minimal Wear',
  'Field-Tested',
  'Well-Worn',
  'Battle-Scarred',
]

const NAME_RE = new RegExp(
  `^(★ )?(StatTrak™ )?(.+?) \\| (.+) \\((${WEARS.join('|')})\\)$`,
)

export function parseSkinName(name) {
  const m = NAME_RE.exec(name)
  if (!m) return null
  return {
    knife: Boolean(m[1]),
    statTrak: Boolean(m[2]),
    weapon: m[3],
    finish: m[4],
    wear: m[5],
  }
}

export function buildSkinName({ knife, statTrak, weapon, finish, wear }) {
  return `${knife ? '★ ' : ''}${statTrak ? 'StatTrak™ ' : ''}${weapon} | ${finish} (${wear})`
}

const finishKey = (weapon, finish) => `${weapon}|${finish.trim().toLowerCase()}`

export function buildCatalog(names) {
  const knives = new Set()
  const finishesByWeapon = new Map()
  // weapon|finish (lowercased) -> every tracked variant of that skin
  const variants = new Map()

  for (const name of names) {
    const skin = parseSkinName(name)
    if (!skin) continue

    if (skin.knife) knives.add(skin.weapon)

    if (!finishesByWeapon.has(skin.weapon)) finishesByWeapon.set(skin.weapon, new Set())
    finishesByWeapon.get(skin.weapon).add(skin.finish)

    const key = finishKey(skin.weapon, skin.finish)
    if (!variants.has(key)) variants.set(key, [])
    variants.get(key).push(skin)
  }

  const sorted = (set) => [...set].sort((a, b) => a.localeCompare(b))
  const weapons = sorted(finishesByWeapon.keys())

  return {
    names: new Set(names),
    guns: weapons.filter((w) => !knives.has(w)),
    knives: weapons.filter((w) => knives.has(w)),
    finishes: new Map(weapons.map((w) => [w, sorted(finishesByWeapon.get(w))])),
    variants,
  }
}

// Every tracked variant of weapon + finish; finish match ignores case.
export function variantsOf(catalog, weapon, finish) {
  return catalog.variants.get(finishKey(weapon, finish)) || []
}

const list = (items) => items.join(', ')

// Resolve the picker's fields to a tracked market name, or explain why
// there isn't one: { name } on success, { error } otherwise.
export function resolveSkin(catalog, { weapon, finish, wear, statTrak }) {
  const typed = finish.trim()
  if (!weapon) return { error: 'Choose a weapon first.' }
  if (!typed) return { error: 'Type the name of the skin.' }

  const matches = variantsOf(catalog, weapon, typed)

  if (matches.length === 0) {
    let error = `There's no ${weapon} skin called "${typed}" in our data.`

    const elsewhere = [...catalog.finishes]
      .filter(([, finishes]) => finishes.some((f) => f.toLowerCase() === typed.toLowerCase()))
      .map(([w]) => w)
    const lower = typed.toLowerCase()
    const close = (catalog.finishes.get(weapon) || []).filter(
      (f) => f.toLowerCase().includes(lower) || lower.includes(f.toLowerCase()),
    )

    if (elsewhere.length > 0) error += ` "${typed}" exists for: ${list(elsewhere)}.`
    else if (close.length > 0) error += ` Did you mean ${list(close.slice(0, 3))}?`
    return { error }
  }

  const exact = matches.find((s) => s.wear === wear && s.statTrak === statTrak)
  if (exact) return { name: buildSkinName(exact) }

  const label = `${weapon} | ${matches[0].finish}`
  const sameType = matches.filter((s) => s.statTrak === statTrak)
  if (sameType.length === 0) {
    return {
      error: statTrak
        ? `${label} isn't tracked in StatTrak™. Uncheck StatTrak™.`
        : `${label} is only tracked in StatTrak™. Check StatTrak™.`,
    }
  }

  const wears = WEARS.filter((w) => sameType.some((s) => s.wear === w))
  return {
    error: `${label}${statTrak ? ' StatTrak™' : ''} isn't tracked in ${wear}. Available: ${list(wears)}.`,
  }
}
