"""Write a README.md catalogue (preview, collection, file) into each asset folder."""
import json, os, glob
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLES = {
    'instruments': ('Instruments', 'One file per instrument; link the `INST_*` (or `CSAPR2`) collection. Root at the origin.'),
    'containers': ('Containers', 'AMF2 containers and shelters with their roof-mounted hardware. `CONT_7_SACR_S2` is the SACR container as configured at S2 (KAWG).'),
    'vehicles': ('Vehicles', 'Farm vehicles/implements and the ARM Bombardier Challenger 850 (`C850_ARM`, gear/flaps/fans driven from custom properties on `C850_root`).'),
    'buildings': ('Buildings and structures', 'Site buildings are stored in site coordinates; the flagpole and center pivots are re-usable (root at the origin).'),
    'plants': ('Plants', 'Prototype collections used by the geometry-node scatterers in the site layers. `_HD` sets are the high-detail trees used at S1/S2; `_S2` grasses are the KAWG lawn variants.'),
    'clouds': ('Clouds', 'Mature snapshots; one collection per snapshot, VDB next to the .blend. Tiled LES fields (LASSO 3x3, UCLA 7x7) keep their periodic tiling.'),
}


def mb(p):
    return f'{os.path.getsize(os.path.join(R, p)) / 1e6:.1f} MB'


for d, (title, blurb) in TITLES.items():
    jobs = json.load(open(os.path.join(R, 'tools/preview_jobs', d + '.json')))
    rows = []
    for j in jobs:
        pv = os.path.relpath(os.path.join(R, j['out']), os.path.join(R, d))
        lib = os.path.relpath(os.path.join(R, j['lib']), os.path.join(R, d))
        img = f'<img src="{pv}" width="260">' if os.path.exists(os.path.join(R, j['out'])) else '(no preview)'
        rows.append(f'| {img} | `{j["coll"]}` | [`{lib}`]({lib}) ({mb(j["lib"])}) |')
    extra = ''
    if d == 'clouds':
        extra = '\n\nVDB files:\n\n' + '\n'.join(f'* `{os.path.relpath(v, os.path.join(R, d))}` ({os.path.getsize(v) / 1e6:.1f} MB)'
                                                for v in sorted(glob.glob(os.path.join(R, d, '*', '*.vdb'))))
    with open(os.path.join(R, d, 'README.md'), 'w') as f:
        f.write(f'# {title}\n\n{blurb}\n\n| Preview | Collection | File |\n|---|---|---|\n' + '\n'.join(rows) + extra + '\n')

# scenes
rows = []
for name in ['M1', 'S1', 'S2']:
    imgs = sorted(glob.glob(os.path.join(R, 'scenes/preview', name + '_*.jpg')))
    layers = sorted(glob.glob(os.path.join(R, 'scenes', name, 'layers', '*.blend')))
    rows.append(f'## {name}\n\n`{name}/{name}.blend` ({mb(f"scenes/{name}/{name}.blend")}) — layers: ' +
                ', '.join(f'`{os.path.relpath(l, os.path.join(R, "scenes"))}` ({os.path.getsize(l) / 1e6:.0f} MB)' for l in layers) + '\n\n' +
                ' '.join(f'<img src="preview/{os.path.basename(i)}" width="400">' for i in imgs))
tests = sorted(glob.glob(os.path.join(R, 'scenes/tests/*.blend')))
trow = []
for t in tests:
    n = os.path.basename(t)[:-6]
    i = glob.glob(os.path.join(R, 'scenes/preview', f'test_{n}_*.jpg'))
    trow.append(f'| `tests/{n}.blend` | ' + (f'<img src="preview/{os.path.basename(i[0])}" width="400">' if i else '') + ' |')
with open(os.path.join(R, 'scenes/README.md'), 'w') as f:
    f.write('# Scenes\n\nEach site scene is a thin file holding cameras, lights, world and render settings; '
            'everything else is linked from the asset folders and from `layers/` (terrain, fields, vegetation, site infrastructure in site coordinates).\n\n'
            + '\n\n'.join(rows) + '\n\n## Test scenes\n\n| Scene | Preview |\n|---|---|\n' + '\n'.join(trow) + '\n')
print('catalogues written')
