# Data sources

## `datasets.csv`

Public facts about public driving datasets, each taken from the dataset's own
paper or website. `points` is the deck's own mapping to city keys in
`make_figures.py`; `license` is a short label, so check the dataset's site
before relying on it.

| Dataset | Source |
|---|---|
| KITTI | Geiger et al., "Are we ready for autonomous driving?", CVPR 2012 |
| KITTI-360 | Liao et al., "KITTI-360", TPAMI 2022 (arXiv 2021) |
| Cityscapes | Cordts et al., "The Cityscapes Dataset", CVPR 2016 |
| nuScenes | Caesar et al., "nuScenes", CVPR 2020 (arXiv 2019) |
| Waymo Open | Sun et al., "Scalability in Perception for Autonomous Driving", CVPR 2020 (arXiv 2019) |
| Argoverse 2 | Wilson et al., "Argoverse 2", NeurIPS Datasets and Benchmarks 2021 |
| A2D2 | Geyer et al., "A2D2: Audi Autonomous Driving Dataset", arXiv 2020 |
| PandaSet | Xiao et al., "PandaSet", ITSC 2021 (released 2020) |
| ONCE | Mao et al., "One Million Scenes for Autonomous Driving", NeurIPS Datasets and Benchmarks 2021 |
| ZOD | Alibeigi et al., "Zenseact Open Dataset", ICCV 2023 |
| Argoverse 1 | Chang et al., "Argoverse", CVPR 2019 |
| Lyft Level 5 | Houston et al., "One Thousand and One Hours", CoRL 2020 |
| nuPlan | Caesar et al., "nuPlan", arXiv 2021 |
| BDD100K | Yu et al., "BDD100K", CVPR 2020 (arXiv 2018) |
| WayveScenes101 | Zürn et al., "WayveScenes101", arXiv 2024 |

## `land.json`

Natural Earth 1:110m Cultural Vectors, Admin 0 – Countries
(`ne_110m_admin_0_countries`, public domain, https://www.naturalearthdata.com).
Derived by keeping the outer ring of each polygon near the map window, every
second vertex, coordinates rounded to 0.1°.
