---
name: bioscience-router
description: "Router für 76 Bioscience-Skills (50 Life-Science Research APIs + 18 NGS-Analyse-Pipelines + 8 Boltz Protein/Molecule Design). Leitet Bioinformatik-Intents an den richtigen Sub-Skill. Use bei AlphaFold, UniProt, Ensembl, NCBI, GWAS, scRNA-seq, RNA-Seq, Protein Design, Metagenomics."
category: bioscience
stack: LOGISCH + GOVERNANCE
risk: high
side_effects: network_calls
requires_approval: false
version: "1.0.0"
last_verified: "2026-08-11"

---
# 🧬 Bioscience Router — 76 Skills

> **Router für `bioscience/`** — Wählt Sub-Skill basierend auf Datenquelle, Assay-Typ oder Analyse-Pipeline.

---

## 🗺️ Routing-Tabelle

### Life-Science Research (50 API-Skills) — `bioscience/life-science-research/`

#### Protein & Struktur

| User sagt... | → Skill | Pfad |
|---|---|---|
| "AlphaFold", "protein structure", "AF2", "AF3" | `alphafold-skill` | `life-science-research/alphafold-skill` |
| "UniProt", "protein database", "protein info" | `uniprot-skill` | `life-science-research/uniprot-skill` |
| "RCSB PDB", "PDB structure", "protein data bank" | `rcsb-pdb-skill` | `life-science-research/rcsb-pdb-skill` |
| "PRIDE", "proteomics", "mass spec data" | `pride-skill` | `life-science-research/pride-skill` |
| "ProteomeXchange", "proteomics repository" | `proteomexchange-skill` | `life-science-research/proteomexchange-skill` |
| "STRING", "protein interaction", "PPI network" | `string-skill` | `life-science-research/string-skill` |
| "InterPro", "IPD", "protein domains" | `ipd-skill` | `life-science-research/ipd-skill` |
| "Human Protein Atlas", "protein expression" | `human-protein-atlas-skill` | `life-science-research/human-protein-atlas-skill` |

#### Gene, Genome & Variation

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Ensembl", "genome browser", "gene annotation" | `ensembl-skill` | `life-science-research/ensembl-skill` |
| "NCBI Entrez", "NCBI gene", "Entrez ID" | `ncbi-entrez-skill` | `life-science-research/ncbi-entrez-skill` |
| "NCBI Datasets", "NCBI genome download" | `ncbi-datasets-skill` | `life-science-research/ncbi-datasets-skill` |
| "NCBI BLAST", "sequence alignment", "BLAST" | `ncbi-blast-skill` | `life-science-research/ncbi-blast-skill` |
| "Bgee", "gene expression", "expression data" | `bgee-skill` | `life-science-research/bgee-skill` |
| "CellxGene", "single cell expression" | `cellxgene-skill` | `life-science-research/cellxgene-skill` |
| "ClinVar", "clinical variant", "pathogenic variant" | `clinvar-variation-skill` | `life-science-research/clinvar-variation-skill` |
| "EVA", "European Variation Archive" | `eva-skill` | `life-science-research/eva-skill` |
| "gnomAD", "population variants", "gnomAD GraphQL" | `gnomad-graphql-skill` | `life-science-research/gnomad-graphql-skill` |
| "cBioPortal", "cancer genomics" | `cbioportal-skill` | `life-science-research/cbioportal-skill` |
| "CIViC", "clinical cancer variants" | `civic-skill` | `life-science-research/civic-skill` |
| "Locus-to-Gene Mapper", "GWAS locus", "V2G" | `locus-to-gene-mapper-skill` | `life-science-research/locus-to-gene-mapper-skill` |
| "GeneBass", "gene burden", "rare variants" | `genebass-gene-burden-skill` | `life-science-research/genebass-gene-burden-skill` |

#### GWAS & PheWAS

| User sagt... | → Skill | Pfad |
|---|---|---|
| "GWAS Catalog", "GWAS study", "trait association" | `gwas-catalog-skill` | `life-science-research/gwas-catalog-skill` |
| "FinnGen PheWAS", "Finnish genetics" | `finngen-phewas-skill` | `life-science-research/finngen-phewas-skill` |
| "Open Targets", "drug target genetics" | `opentargets-skill` | `life-science-research/opentargets-skill` |
| "UKB TOPMed PheWAS" | `ukb-topmed-phewas-skill` | `life-science-research/ukb-topmed-phewas-skill` |
| "BioBank Japan PheWAS" | `biobankjapan-phewas-skill` | `life-science-research/biobankjapan-phewas-skill` |
| "TPMI PheWAS" | `tpmi-phewas-skill` | `life-science-research/tpmi-phewas-skill` |
| "eQTL Catalogue", "eQTL data" | `eqtl-catalogue-skill` | `life-science-research/eqtl-catalogue-skill` |
| "GTEx eQTL", "tissue eQTL" | `gtex-eqtl-skill` | `life-science-research/gtex-eqtl-skill` |
| "EpiGraphDB", "epi graph database" | `epigraphdb-skill` | `life-science-research/epigraphdb-skill` |

#### Chemie, Pathways & Ontologie

| User sagt... | → Skill | Pfad |
|---|---|---|
| "ChEMBL", "bioactivity", "drug target" | `chembl-skill` | `life-science-research/chembl-skill` |
| "PubChem", "chemical compound", "PUGREST" | `pubchem-pug-skill` | `life-science-research/pubchem-pug-skill` |
| "ChEBI", "chemical ontology" | `chebi-skill` | `life-science-research/chebi-skill` |
| "BindingDB", "binding affinity" | `bindingdb-skill` | `life-science-research/bindingdb-skill` |
| "Reactome", "pathway database" | `reactome-skill` | `life-science-research/reactome-skill` |
| "QuickGO", "GO terms", "gene ontology" | `quickgo-skill` | `life-science-research/quickgo-skill` |
| "Rhea", "biochemical reactions" | `rhea-skill` | `life-science-research/rhea-skill` |
| "EFO Ontology", "experimental factor" | `efo-ontology-skill` | `life-science-research/efo-ontology-skill` |
| "HMDB", "human metabolome" | `hmdb-skill` | `life-science-research/hmdb-skill` |
| "MetaboLights", "metabolomics" | `metabolights-skill` | `life-science-research/metabolights-skill` |
| "PharmGKB", "pharmacogenomics" | `pharmgkb-skill` | `life-science-research/pharmgkb-skill` |

#### Literatur & Klinische Studien

| User sagt... | → Skill | Pfad |
|---|---|---|
| "PubMed Central", "PMC", "full text" | `ncbi-pmc-skill` | `life-science-research/ncbi-pmc-skill` |
| "bioRxiv", "preprint" | `biorxiv-skill` | `life-science-research/biorxiv-skill` |
| "ClinicalTrials.gov", "clinical trial" | `clinicaltrials-skill` | `life-science-research/clinicaltrials-skill` |
| "NCBI Clinical Tables" | `ncbi-clinicaltables-skill` | `life-science-research/ncbi-clinicaltables-skill` |
| "ENCODE", "epigenomics data" | `encode-skill` | `life-science-research/encode-skill` |

#### Sonstige

| User sagt... | → Skill | Pfad |
|---|---|---|
| "RNAcentral", "ncRNA" | `rnacentral-skill` | `life-science-research/rnacentral-skill` |
| "MGnify", "metagenomics" | `mgnify-skill` | `life-science-research/mgnify-skill` |
| "BioStudies", "ArrayExpress" | `biostudies-arrayexpress-skill` | `life-science-research/biostudies-arrayexpress-skill` |
| "Research Router", "which bioscience tool" | `research-router-skill` | `life-science-research/research-router-skill` |

---

### NGS Analysis (18 Pipeline-Skills) — `bioscience/ngs-analysis/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "NGS router", "which NGS pipeline" | `ngs-analysis-router` | `ngs-analysis/ngs-analysis-router` |
| "RNA-Seq", "bulk RNAseq", "transcriptome" | `ngs-bulk-rnaseq` | `ngs-analysis/ngs-bulk-rnaseq` |
| "RNA-Seq differential expression", "DEG" | `ngs-bulk-rnaseq-differential-expression` | `ngs-analysis/ngs-bulk-rnaseq-differential-expression` |
| "RNA-Seq counts QC" | `ngs-bulk-rnaseq-counts-qc` | `ngs-analysis/ngs-bulk-rnaseq-counts-qc` |
| "scRNA-seq", "single cell RNA" | `ngs-scrna-seq` | `ngs-analysis/ngs-scrna-seq` |
| "scRNA-seq QC", "single cell QC" | `scrna-seq-qc` | `ngs-analysis/scrna-seq-qc` |
| "ATAC-seq", "ATACseq peaks" | `ngs-atacseq-peaks-qc` | `ngs-analysis/ngs-atacseq-peaks-qc` |
| "ChIP-seq", "CUT&RUN peaks" | `ngs-chip-cutrun-peaks-qc` | `ngs-analysis/ngs-chip-cutrun-peaks-qc` |
| "epigenomics peaks", "histone marks" | `ngs-epigenomics-peaks` | `ngs-analysis/ngs-epigenomics-peaks` |
| "DNA variant calling", "germline variants" | `ngs-dna-variant-calling` | `ngs-analysis/ngs-dna-variant-calling` |
| "DNA germline variants", "WGS germline" | `ngs-dna-germline-variants` | `ngs-analysis/ngs-dna-germline-variants` |
| "DNA somatic variants", "tumor variants" | `ngs-dna-somatic-variants` | `ngs-analysis/ngs-dna-somatic-variants` |
| "UMI panel variants", "targeted sequencing" | `ngs-dna-umi-panel-variants` | `ngs-analysis/ngs-dna-umi-panel-variants` |
| "fastq QC", "fastqc", "read quality" | `ngs-fastq-qc` | `ngs-analysis/ngs-fastq-qc` |
| "BCL to fastq", "bcl2fastq", "demultiplex" | `ngs-bcl-to-fastq` | `ngs-analysis/ngs-bcl-to-fastq` |
| "amplicon microbiome", "16S", "ITS" | `ngs-amplicon-microbiome` | `ngs-analysis/ngs-amplicon-microbiome` |
| "shotgun metagenomics", "metagenome" | `ngs-shotgun-metagenomics` | `ngs-analysis/ngs-shotgun-metagenomics` |
| "NGS runtime env", "conda NGS", "NGS setup" | `ngs-runtime-env` | `ngs-analysis/ngs-runtime-env` |

---

### Boltz (8 Skills) — `bioscience/boltz-api-cli/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Boltz CLI setup", "install Boltz" | `boltz-cli-setup` | `boltz-api-cli/boltz-cli-setup` |
| "Boltz protein design" | `boltz-protein-design` | `boltz-api-cli/boltz-protein-design` |
| "Boltz protein screen" | `boltz-protein-screen` | `boltz-api-cli/boltz-protein-screen` |
| "Boltz structure binding", "binding prediction" | `boltz-structure-and-binding` | `boltz-api-cli/boltz-structure-and-binding` |
| "Boltz small molecule design" | `boltz-small-molecule-design` | `boltz-api-cli/boltz-small-molecule-design` |
| "Boltz small molecule screen" | `boltz-small-molecule-screen` | `boltz-api-cli/boltz-small-molecule-screen` |
| "Boltz ADME", "small molecule ADME" | `boltz-small-molecule-adme` | `boltz-api-cli/boltz-small-molecule-adme` |
| "Boltz check status", "Boltz job status" | `boltz-check-status` | `boltz-api-cli/boltz-check-status` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ Protein/Struktur? → life-science-research/<protein-skill>
├─ Gen/Variante/GWAS? → life-science-research/<gene-skill>
├─ Chemie/Pathway? → life-science-research/<chem-skill>
├─ NGS Pipeline? → ngs-analysis/<assay-skill>
├─ Boltz/Protein Design? → boltz-api-cli/<boltz-skill>
├─ Unklar? → life-science-research/research-router-skill ODER ngs-analysis/ngs-analysis-router
└─ Kombiniert? → Starte mit Router, dann Spezialisten
```

---

## Verwendung

```
User: "Finde die AlphaFold Struktur von P53"
→ Router: bioscience/life-science-research/alphafold-skill

User: "RNA-Seq differentielle Expression analysieren"
→ Router: bioscience/ngs-analysis/ngs-bulk-rnaseq-differential-expression

User: "Designe ein Protein mit Boltz"
→ Router: bioscience/boltz-api-cli/boltz-protein-design
```

_76 Skills · 50 Life-Science APIs + 18 NGS Pipelines + 8 Boltz · August 2026_
