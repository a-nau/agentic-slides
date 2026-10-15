# Borrowed figures — Krizhevsky, Sutskever & Hinton (NIPS 2012)

Crops rendered from the official proceedings PDF (`pdftoppm -r 200`), cropped
to the figure, no other edits. Every slide that shows one carries a visible
"Figure N from Krizhevsky et al. 2012" caption linking to the paper page.

| File | Source | Figure | Page |
|---|---|---|---|
| `fig1-relu-vs-tanh.png` | https://papers.nips.cc/paper_files/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf | Figure 1 — training error vs epochs, ReLU (solid) vs tanh (dashed), CIFAR-10 four-layer net | 3 |
| `fig2-architecture.png` | same PDF | Figure 2 — the two-GPU architecture, as printed (upper lane clipped in the original) | 5 |
| `fig3-kernels.png` | same PDF | Figure 3 — the 96 learned 11×11×3 first-layer kernels, GPU 1 top, GPU 2 bottom | 6 |
| `fig4-predictions.jpg` | same PDF | Figure 4 — eight test images with top-5 predictions (left); five test images and their six nearest neighbours in the last hidden layer (right) | 8 |

Paper landing page: https://papers.nips.cc/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html

**License:** no license stated. The PDF carries no copyright line or
reproduction notice (checked pages 1 and 9 with `pdftotext`). The figures
are reproduced here for scholarly commentary with attribution; the copyright
remains with the authors / NeurIPS.

No official project page exists for this paper; the authors' code was
released separately as cuda-convnet (later cuda-convnet2,
https://github.com/akrizhevsky/cuda-convnet2), which ships no figures used
here.
