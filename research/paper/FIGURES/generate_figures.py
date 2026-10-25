"""Generate reproducible figures for the PolarisLex preliminary paper.

All numeric values are copied from the frozen Phase 3 independent metrics and
run report. The architecture diagrams show implemented components and mark
optional/unmeasured services explicitly.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


OUT = Path(__file__).resolve().parent
CONFIGS = ["A baseline", "B decomposition", "C polarity-aware", "D combined"]
METRICS = {"Precision": [0, 0, 0, 0], "Recall": [0, 0, 0, 0], "F1": [0, 0, 0, 0], "Specificity": [1, 1, 1, 1]}


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def box(ax, x, y, w, h, text, color="#D9EAF7", edge="#2F5597", dashed=False):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.2, facecolor=color, edgecolor=edge,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8, wrap=True)


def arrow(ax, x1, y1, x2, y2, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1, color="#404040", linestyle="--" if dashed else "-"))


def figure1():
    fig, ax = plt.subplots(figsize=(12, 4.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 4.2); ax.axis("off")
    ax.set_title("Figure 1. PolarisLex implemented architecture and measured research path", fontsize=12, pad=12)
    box(ax, .2, 1.7, 1.5, .8, "Policy input\nPDF / DOCX / HTML / TXT")
    box(ax, 2.0, 1.7, 1.7, .8, "Document pipeline\nclean → section → clause")
    box(ax, 4.0, 1.7, 1.6, .8, "Policy clauses\ncontext + entities")
    box(ax, 6.0, 2.4, 1.7, .8, "Legal rules\nDutyRule + elements")
    box(ax, 6.0, 1.1, 1.7, .8, "GraphIR\nnodes + relations")
    box(ax, 8.1, 1.7, 1.7, .8, "Evidence\nretrieval + polarity")
    box(ax, 10.2, 1.7, 1.5, .8, "Classifier\nstatus + report")
    for a,b in [(1.7,2.0),(3.7,4.0),(5.6,8.1),(9.8,10.2)]: arrow(ax,a,2.1,b,2.1)
    arrow(ax,5.6,2.2,6.0,2.75); arrow(ax,7.7,2.75,8.1,2.25); arrow(ax,7.7,1.5,8.1,2.0)
    ax.text(8.95, .55, "Measured Phase 3 path: keyword stub\nQdrant / Neo4j / JEV not used", ha="center", fontsize=8, color="#9C0006")
    box(ax, 8.1, .25, 1.7, .55, "Optional production\nvector / graph services", color="#FCE4D6", edge="#C55A11", dashed=True)
    arrow(ax,8.95,.8,8.95,1.7, dashed=True)
    save(fig,"figure1_architecture")


def figure2():
    fig, ax = plt.subplots(figsize=(12, 3.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 3.6); ax.axis("off")
    ax.set_title("Figure 2. Experimental methodology", fontsize=12, pad=12)
    steps=[("42 synthetic cases", "33 train / 9 test"),("Frozen test split", "same gold labels"),("A–D configurations", "baseline / elements / polarity / combined"),("Keyword-stub retrieval", "no Qdrant"),("Metrics", "binary + multiclass + elements")]
    xs=[.2,2.6,5.0,7.5,9.9]
    for i,(a,b) in enumerate(steps):
        box(ax,xs[i],1.35,1.8,.9,f"{a}\n{b}",color="#E2F0D9" if i<2 else "#D9EAF7")
        if i<4: arrow(ax,xs[i]+1.8,1.8,xs[i+1],1.8)
    ax.text(6, .5, "Positive class = covered; all other statuses = not covered.\nTP=0, FP=0, TN=7, FN=2 for every configuration.", ha="center", fontsize=9)
    save(fig,"figure2_methodology")


def figure3():
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); x=np.arange(4); width=.18
    colors=["#4472C4","#ED7D31","#A5A5A5","#70AD47"]
    for i,(metric,vals) in enumerate(METRICS.items()): ax.bar(x+(i-1.5)*width, vals, width, label=metric, color=colors[i])
    ax.set_xticks(x, ["A","B","C","D"]); ax.set_ylim(0,1.12); ax.set_ylabel("Score"); ax.set_title("Figure 3. Configuration comparison (n=9 test cases)")
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(.5,1.0)); ax.text(.5,-.18,"Precision, recall, and F1 are all zero; specificity is 1.0 because no case was predicted covered.",transform=ax.transAxes,ha="center",fontsize=8)
    ax.grid(axis="y",alpha=.25); save(fig,"figure3_configuration_comparison")


def figure4():
    fig, ax = plt.subplots(figsize=(4.8,4.0)); mat=np.array([[0,2],[0,7]]); im=ax.imshow(mat,cmap="Blues",vmin=0,vmax=7)
    ax.set_xticks([0,1], ["Predicted\ncovered","Predicted\nnot covered"]); ax.set_yticks([0,1],["Reference\ncovered","Reference not\ncovered"])
    for i in range(2):
        for j in range(2): ax.text(j,i,f"{['TP','FN','FP','TN'][i*2+j]} = {mat[i,j]}",ha="center",va="center",color="white" if mat[i,j]>3 else "black",fontsize=10)
    ax.set_title("Figure 4. Binary confusion matrix\npositive class = covered"); fig.colorbar(im,ax=ax,shrink=.8); save(fig,"figure4_confusion_matrix")


def figure5():
    fig, ax = plt.subplots(figsize=(8.5,4.5)); ax.axis("off"); ax.set_title("Figure 5. Feature impact and case-level error analysis",fontsize=12,pad=12)
    rows=[("Decomposition B vs A","0 final-status changes","No aggregate improvement"),("Polarity C vs A","2 changes: SYN_010, SYN_027","partial → violation; both disagree with reference"),("Combined D vs A","2 changes: SYN_010, SYN_027","Same as polarity-aware; no metric improvement")]
    y=2.8
    for label,change,note in rows:
        box(ax,.4,y,2.4,.75,label,color="#D9EAF7"); arrow(ax,2.9,y+.38,3.5,y+.38); box(ax,3.6,y,2.2,.75,change,color="#FFF2CC",edge="#BF9000"); arrow(ax,5.9,y+.38,6.5,y+.38); box(ax,6.6,y,1.6,.75,note,color="#FCE4D6",edge="#C55A11"); y-=1.05
    ax.text(4.3,.25,"Interpretation: feature activation was observed, but no configuration improved covered-class recall or F1.",ha="center",fontsize=9)
    save(fig,"figure5_feature_impact")


if __name__ == "__main__":
    figure1(); figure2(); figure3(); figure4(); figure5()
    print("Generated five PNG and five SVG figures in", OUT)
