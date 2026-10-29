import { describe, expect, it } from 'vitest'
import { buildCatalog, buildSkinName, parseSkinName, resolveSkin } from './skins'

const catalog = buildCatalog([
  'AK-47 | Redline (Field-Tested)',
  'AK-47 | Redline (Minimal Wear)',
  'StatTrak™ AK-47 | Redline (Field-Tested)',
  'AK-47 | Vulcan (Factory New)',
  'AWP | Asiimov (Field-Tested)',
  'M4A4 | Asiimov (Field-Tested)',
  '★ Karambit | Doppler (Factory New)',
  '★ StatTrak™ Karambit | Doppler (Factory New)',
  'Sticker | Something',
])

const pick = (overrides) => ({
  weapon: 'AK-47',
  finish: 'Redline',
  wear: 'Field-Tested',
  statTrak: false,
  ...overrides,
})

describe('parseSkinName / buildSkinName', () => {
  it('round-trips StatTrak knives', () => {
    const name = '★ StatTrak™ Karambit | Doppler (Factory New)'
    const skin = parseSkinName(name)
    expect(skin).toEqual({
      knife: true,
      statTrak: true,
      weapon: 'Karambit',
      finish: 'Doppler',
      wear: 'Factory New',
    })
    expect(buildSkinName(skin)).toBe(name)
  })

  it('returns null for names without a weapon and wear', () => {
    expect(parseSkinName('Sticker | Something')).toBeNull()
  })
})

describe('buildCatalog', () => {
  it('splits guns from knives and lists finishes per weapon', () => {
    expect(catalog.guns).toEqual(['AK-47', 'AWP', 'M4A4'])
    expect(catalog.knives).toEqual(['Karambit'])
    expect(catalog.finishes.get('AK-47')).toEqual(['Redline', 'Vulcan'])
  })
})

describe('resolveSkin', () => {
  it('builds the market name, ignoring case and spaces in the finish', () => {
    expect(resolveSkin(catalog, pick({ finish: '  redline ' }))).toEqual({
      name: 'AK-47 | Redline (Field-Tested)',
    })
  })

  it('adds the knife star back', () => {
    expect(
      resolveSkin(catalog, pick({ weapon: 'Karambit', finish: 'doppler', wear: 'Factory New', statTrak: true })),
    ).toEqual({ name: '★ StatTrak™ Karambit | Doppler (Factory New)' })
  })

  it('suggests close finishes on a typo', () => {
    const { error } = resolveSkin(catalog, pick({ finish: 'Red' }))
    expect(error).toMatch(/no AK-47 skin called "Red"/)
    expect(error).toMatch(/Did you mean Redline\?/)
  })

  it('points to the right weapon when the finish exists elsewhere', () => {
    const { error } = resolveSkin(catalog, pick({ finish: 'asiimov' }))
    expect(error).toMatch(/exists for: AWP, M4A4/)
  })

  it('lists the wears that are tracked', () => {
    const { error } = resolveSkin(catalog, pick({ wear: 'Battle-Scarred' }))
    expect(error).toBe(
      "AK-47 | Redline isn't tracked in Battle-Scarred. Available: Minimal Wear, Field-Tested.",
    )
  })

  it('says when StatTrak is not tracked', () => {
    const { error } = resolveSkin(catalog, pick({ finish: 'Vulcan', wear: 'Factory New', statTrak: true }))
    expect(error).toMatch(/isn't tracked in StatTrak™/)
  })

  it('asks for the missing fields', () => {
    expect(resolveSkin(catalog, pick({ weapon: '' })).error).toMatch(/Choose a weapon/)
    expect(resolveSkin(catalog, pick({ finish: ' ' })).error).toMatch(/Type the name/)
  })
})
