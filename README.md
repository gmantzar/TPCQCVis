# TPCQCVis
## Index:
1. [Introduction](#introduction)
1. [Setting up](#setting-up)
1. [User Guide](#user-guide)
1. [Developers Guide](#developers-guide)
   - [Module reference](#module-reference)

## Introduction:
The monitoring of the ALICE TPC quality control data in RUN3 is planned to be done using the Jupyter environment, where libraries e.g. Bokeh plotter can be used which enables very user-friendly interactivity capabilities. We have PyRoot based notebooks for visualizing the Root Object outputs from central sync and async QC. And, we have expert dashboards made with RootInteractive using skimmed data.

The webinterface for generated reports is located at [alice-tpc-qc.web.cern.ch](https://alice-tpc-qc.web.cern.ch/)

## Setting up:
1. Install [O2](https://alice-doc.github.io/alice-analysis-tutorial/building/custom.html) & [Quality Control](https://github.com/AliceO2Group/QualityControl)
2. Set up GRID certificate (if not already done)
   1. Create and download certificate from [ca.cern.ch/ca](https://ca.cern.ch/ca/)
   2. Convert to right format as described in [alice-analysis-tutorial](https://alice-doc.github.io/alice-analysis-tutorial/start/cert.html#convert-your-certificate-for-using-the-grid-tools)
   3. Test certificate as described in [alice-analysis-tutorial](https://alice-doc.github.io/alice-analysis-tutorial/start/cert.html#test-your-certificate) or run `alien.py` with O2 loaded.
3. Enter QC environment
   1. Install TPCQCVis
      1. Clone this repo.
         1. `git clone https://github.com/bulukutlu/TPCQCVis.git`
      2. Set the following environment variables in your `.bashrc` or `.bash_profile` etc.:
          - `TPCQCVIS_DIR`: Directory path where the code resides.
          - `TPCQCVIS_DATA`: Directory path where data will be downloaded.
          - `TPCQCVIS_REPORT`: Directory path where reports will be stored.

          The following are **optional** overrides for deployment-specific values
          (they default to the historical hard-coded values, so nothing needs to
          be set for the standard TPC-QC deployment). They exist so the pipeline
          is no longer welded to one maintainer's identity:
          - `TPCQCVIS_REPORT_SENDER`: address that sends the daily MonALISA "async
            productions completed" mail (used by `dailyAsyncFromEmail.py`).
          - `TPCQCVIS_MATTERMOST_WEBHOOK`: Mattermost incoming-webhook URL.
          - `TPCQCVIS_RSYNC_TARGET`, `TPCQCVIS_UPDATE_HOST`, `TPCQCVIS_UPDATE_CMD`,
            `TPCQCVIS_SSH_SECRET`: publishing targets used when uploading reports.
          - `TPCQCVIS_LOGLEVEL`: logging verbosity (`INFO` by default, `DEBUG` for more).
      3. Install the package: `pip install -e $TPCQCVIS_DIR`
          > If you add new modules under `TPCQCVis/` later, re-run this so the
          > editable install picks them up.
      4. Check if installation is OK: `python $TPCQCVIS_DIR/post_install_checks.py`
   2. [Optional] Install [RootInteractive](https://github.com/miranov25/RootInteractive)

## User guide:
### Creating reports with templates
> [!TIP]
> More detailed examples for custom report creation down below in Chapter: [Full workflow example](#full-workflow-example)
The worflow for the report creation is as follows:
1. During offline production async QC tasks are run. A QC merger process gathers all files for a run in to on file. The produced QC output goes into the QCDB (which can be visualized via the QCG) but also to the alien with the name `QC_fullrun.root`
2. We download the `QC_fullrun.root` objects from alien.
    > Implemented in `tools/downloadFromAlien.py`
3. We extract the TPC relevant objects and write them to a new root file. We also run postprocessing on this file.
    > Implemented in `tools/runPlotter.py`
4. We create reports using jupyter notebook templates with the QC files as input.
    > Implemented in `tools/generateReport.py`
5. The generated reports are uploaded to the eos project folder (located at `/eos/project-a/alice-tpc-qc/www` also accesible via CernBox). The WebServices handle the displaying of the reports for viewers.
    > Implemented in `tools/syncAndUpload.py`

To avoid having to go through all of the steps above everytime, there are automation scripts implemented.

### Daily productions: recommended trigger (`pollProductions.py`)

> **Recommended over the e-mail trigger below.** It does not depend on any
> individual's Gmail account, cannot be broken by a change in the notification
> e-mail's wording, and is idempotent/resumable.

Instead of scraping the MonALISA notification e-mail, `tools/pollProductions.py`
reacts to the artifacts directly: it asks AliEn which `QC_fullrun.root` files
exist for the periods you care about, remembers what it already handled in a
small state file (`<TPCQCVIS_REPORT>/poll_state.json`), and processes only the
new ones through the usual download→plot→report chain (`qc_master.py`).

```
# List what is new without doing anything:
python $TPCQCVIS_DIR/TPCQCVis/tools/pollProductions.py --year 2026 --periods LHC26ai LHC26ae --apass apass1
# Actually download/plot/report the new productions:
python $TPCQCVIS_DIR/TPCQCVis/tools/pollProductions.py --year 2026 --periods LHC26ai --process -t 10
```

Schedule it with cron/systemd (e.g. daily) — because it is idempotent, a missed
run is simply picked up next time. The GRID certificate the pipeline already
needs is the only credential required.

### Daily Async Report (legacy e-mail trigger)
```
python $TPCQCVIS_DIR/TPCQCVis/tools/dailyAsyncFromEmail.py [--date DATE] [--dates DATES...] [--num_threads NUM_THREADS] [--schedule SCHEDULE] [--mattermost]
```

> Every day at 10:00 CERN time the MonALISA interface sends an email to the alice-dpg-async-qc mailing group the list of async productions completed that day.

The `tools/dailyAsyncFromEmail.py` script allows the automatic generation of reports for the productions of a given day.

- Before running the script, you need to authorize access to Gmail by following these steps:
   - Create an OAuth *Desktop* client in a Google Cloud project for the mailbox that
     is subscribed to the `alice-dpg-async-qc` list, and place the downloaded
     `credentials.json` file in the directory specified by `TPCQCVIS_DIR`.
   - Set `TPCQCVIS_REPORT_SENDER` to the address that sends the MonALISA mail
     (defaults to the original sender for backwards compatibility).
   - Run the script once interactively on a machine with a browser to mint
     `token.json`, then copy it to the server. Subsequent runs refresh the token
     automatically (non-interactively), so the scheduled job works headless — this
     was previously broken because the refresh path was disabled.

**Options:**
  - `--num_threads`: how many threads to use when running in parallel (downloading still done sequentially due to LRZ limitations)
  - `--date`: specify date (example: `--date 08.04.2024`)
  - `--dates`: specify dates (example: `--dates 06.04.2024 07.04.2024 08.04.2024`)
  - `--schedule`: Schedule automatic running of the script everyday at specified time (example: `--schedule 1015`)
  - `--mattermost`: Send overview of generated reports to TPC-AsyncQC channel
  
**Example:**
```
python $TPCQCVIS_DIR/TPCQCVis/tools/dailyAsyncFromEmail.py --num_threads 10 --date 13.05.2024
```

### QC Master Automation
```
python $TPCQCVIS_DIR/TPCQCVis/tools/qc_master.py [--path PATH] [--apass APASS] [-d] [-p] [-r] [-rr] [-t NUM_THREADS] [period_list...]
```
This script allow the calling of different parts of the production chain for multiple different periods automatically.

**Options:**
- period_list: List of period strings.
- `-d` or `--download`: Run the download command.
- `-p` or `--plot`: Run the plotter command.
- `-r` or `--report`: Run the report command.
- `-rr` or `--rerun`: Rerun plotter for existing periods.
- `--path`: Path string for the generateReport command.
- `--apass`: Apass string for the generateReport command.
- `-t` or `--num_threads`: Number of threads to be used - (default: 1).

**Examples:**
```
python $TPCQCVIS_DIR/TPCQCVis/tools/qc_master.py --path $TPCQCVIS_DATA/2023/ --apass apass3 --download --plot --report LHC23zzk
```

> To upload generated reports to the webpage, afterwards do: `python $TPCQCVIS_DIR/TPCQCVis/tools/syncAndUpload.py'`

### MonteCarlo
The QC output of the MonteCarlo productions is a bit differently structured, as such the downloading has to be handled with a different script.

```
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadSim.py [alien paths ...]
```
or
```
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadSim.py [alien dir]
```
**Example:**
```
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadSim.py --dir /alice/sim/2024/LHC24b1b/0/
```

After downloading the files and cd'ing to their location, the QC plot files can again be generated using:
```
python $TPCQCVIS_DIR/TPCQCVis/tools/runPlotter.py -t 10 $PWD/
```
**Comparing to Data:**

For comparing MC against the data runs they were anchored to, a report template exist at: `reports/TPC_AQC_Template_CompareRunToMC.ipynb`
To generate comparison reports use the `tools/generateMCComparisonReports.py` tool. For this set in the python script the info for the wanted comparison. e.g.:
```
### Part to set
path = f"{DATADIR}/sim/2024/"
period = "LHC24e2" 
passName = "" #keep empty ("") if MC
pathComparison = f"{DATADIR}/2023/"
periodListComparison =  ["LHC23zzf","LHC23zzg","LHC23zzh"]
passNameListComparison = ["apass3","apass3","apass3"]
```
Afterwards, run the script:
```
python $TPCQCVIS_DIR/TPCQCVis/tools/generatMCComparisonReports.py 
```
Which will put the reports in to the corresponding data folder (direcotry with .root files for MC). To upload you can use the syncAndUpload tool.

> [!TIP]
> Normally, the MC runs are very stable and don't need to be checked on their own (unless requested). If you want, you can generate the normal QC reports using the `tools/generateReport.py` script.

To convert the saved notebook into html report see [Exporting Notebooks](#exporting-notebooks)

## Developers guide:
This repository mainly contains the automation scripts described above and ROOT functions for making nicer plots and postprocessing.

- The implementation is located at `$TPCQCVIS_DIR/TPCQCVis/src`.
- For testing functionality there are notebooks located at `$TPCQCVIS_DIR/TPCQCVis/tests`.
- Notebook demonstrating some core functions [UserGuide.ipynb](TPCQCVis/tutorials/UserGuide.ipynb)
- Other demos can be found at `TPCQCVis/tutorials/` (not up to date)

### Module reference

The Python package lives under `TPCQCVis/` and is organised into four layers:
`core/` (shared infrastructure), `tools/` (runnable pipeline scripts), `src/`
(the PyROOT plotting/QC library used by the report notebooks) and `reports/`
(the notebook templates). The C++ ROOT macros live in `macro/`.

#### `TPCQCVis/core/` — shared infrastructure

Cross-cutting helpers imported by the tools so that configuration, path parsing,
subprocess handling and logging live in one place instead of being copy-pasted.

| Module | Responsibility |
| --- | --- |
| `config.py` | Reads and **validates** the environment (`TPCQCVIS_DIR/DATA/REPORT`) once, with clear error messages, and exposes the optional deployment overrides (sender, Mattermost webhook, publishing targets) as a single `settings` object. |
| `paths.py` | The single tested parser for the `{year}/{period}/{apass}/{run}` filesystem convention: `run_number_from_file`, `list_runs`, `ProductionPath`, etc. Replaces the ad-hoc filename slicing that used to be scattered across the tools. |
| `shell.py` | `run()` wrapper around `subprocess`: logs every command, surfaces failures (return codes are no longer silently ignored), and can optionally raise. |
| `logging_setup.py` | `get_logger()` / `configure_logging()` — consistent, timestamped logging (level via `TPCQCVIS_LOGLEVEL`). |
| `state.py` | `StateStore` — a tiny atomic JSON store recording which `(period, apass, run)` productions have been processed, plus a per-source *watermark*. Used by `pollProductions.py` to stay idempotent. |

#### `TPCQCVis/tools/` — runnable scripts

**Orchestration / automation**

| Script | What it does |
| --- | --- |
| `qc_master.py` | Fans out the whole chain (download / plot / report) over many periods and passes in parallel. Options: `-d/--download`, `-p/--plot`, `-r/--report`, `-rr/--rerun`, `--path`, `--apass`, `-t/--num_threads`, and a positional `period_list` (defaults to every period folder under `--path`). Used by [Approach 2](#approach-2--qc-master). |
| `pollProductions.py` | **Recommended trigger.** Polls AliEn for new `QC_fullrun.root` files for given periods, filters against the `StateStore`, and runs the chain only for new productions. Options: `--year`, `--periods`, `--apass`, `-t`, `--state`, `--process`. See [recommended trigger](#daily-productions-recommended-trigger-pollproductionspy). |
| `dailyAsyncFromEmail.py` | Legacy trigger that reads the daily MonALISA e-mail (Gmail API) and runs the chain for that day's productions. Options: `--date`, `--dates`, `--schedule`, `--num_threads`, `--mattermost`, `--catch_up`, `--no_plot/--no_report/--no_upload`. See [legacy e-mail trigger](#daily-async-report-legacy-e-mail-trigger). |

**Pipeline stages**

| Script | What it does |
| --- | --- |
| `downloadFromAlien.py` | Downloads data QC files from AliEn and enriches them (Bethe-Bloch TTree, optional dead-channel maps). See [Approach 1, Step 1](#step-1--download-the-raw-qc-files-downloadfromalienpy). |
| `runPlotter.py` | Extracts TPC objects into `{run}_QC.root`, adds moving-window overlays, run parameters and period postprocessing. See [Approach 1, Step 2](#step-2--extract-tpc-plots-runplotterpy). |
| `generateReport.py` | Renders the run / period / comparison HTML reports from the notebook templates. See [Approach 1, Step 3](#step-3--generate-the-html-reports-generatereportpy). |
| `periodPostprocessing.py` | Builds the period-level `periodOverview.root` (aggregated trends and median distributions) consumed by the period report. Invoked automatically by `runPlotter.py`. |
| `syncAndUpload.py` | Moves and `rsync`s the finished reports to the eos web folder and refreshes the server. See [Approach 1, Step 4](#step-4--publish-to-the-webpage-syncanduploadpy). |
| `moveFiles.py` | Generic helper: move files matching a pattern from `-i` to `-o` while preserving the directory structure (used by the publish step). |

**MonteCarlo / time-slices**

| Script | What it does |
| --- | --- |
| `downloadSim.py` | Downloads the differently-structured MonteCarlo QC output (`tpcStandardQC.root`) from `/alice/sim/...`. Options: `--dir` (a directory of runs) or `--paths` (explicit AliEn paths). See [MonteCarlo](#montecarlo). |
| `generateMCComparisonReports.py` | Generates MC-vs-data comparison reports from `TPC_AQC_Template_CompareRunToMC.ipynb`. The comparison (period, anchored data periods/passes) is configured by editing the variables at the top of the script. |
| `getAllQCtimeslices.py` | Downloads every per-time-slice `QC.root` for a production (`--path`), for detailed time-dependence studies. |

#### `TPCQCVis/src/` — plotting & QC library

PyROOT functions used mostly from inside the report notebooks. These produce the
actual plots and quality flags.

| Module | Responsibility |
| --- | --- |
| `drawHistograms.py` | `drawHistograms(...)` — the main plotting routine: draws one histogram per input file, supports pads, log scales, normalisation, quality-colouring and side-by-side comparison with ratio panels. |
| `drawTrending.py` | `drawTrending(...)` — builds a run-by-run trending histogram of a chosen quantity (mean, entries, stdDev, a fit parameter, or KL divergence). |
| `drawMultiTrending.py` | `drawMultiTrending(...)` — trending for multi-pad canvases (one trend per pad, e.g. per sector). |
| `checkHistograms.py` | `checkHistograms(...)` — evaluates a per-histogram quality expression and returns `GOOD`/`BAD` flags used to colour the plots. |
| `checkTrending.py` | `checkTrending(...)` — flags trending points as `GOOD`/`MEDIUM`/`BAD` against configurable sigma bands. |
| `utility.py` | Shared helpers: recursive `getHistogram`, moving-window drawing, PID-profile extraction, `downloadAttempts` (robust AliEn copy with retries), range harmonisation, etc. |
| `emptyClustersChecker.py` | Detects empty/outlier regions in 2D cluster maps using DBSCAN clustering. |
| `drawBetheBloch.py` | Draws the Bethe-Bloch expectation lines from the stored fit parameters. |
| `palette.py` | Shared colour palette definitions for the plots. |

#### `TPCQCVis/reports/` — notebook templates

Parameterised Jupyter notebooks executed by `generateReport.py`. The template's
placeholder tokens (`myPeriod`, `myPass`, `myPath`, run number, …) are replaced
before execution.

| Template | Produces |
| --- | --- |
| `TPC_AQC_Template_Run.ipynb` | Single-run report. |
| `TPC_AQC_Template_Period.ipynb` | Period overview (all runs of one pass). |
| `TPC_AQC_Template_ComparePasses.ipynb` | Comparison of a pass against the other passes of the period. |
| `TPC_AQC_Template_CompareRunToMC.ipynb` | MonteCarlo vs anchored-data comparison (used by `generateMCComparisonReports.py`). |
| `TPC_AQC_Template_Period_CompareToMedian.ipynb` | Period report comparing each run to the period median. |
| `TPC_AQC_Template_Run_TimeSlices.ipynb` | Run report broken down into time slices. |
| `TPC_AQC_Template_WeeklyRuns.ipynb` | Weekly summary across runs. |

Finished custom/one-off reports live in `reports/custom/`.

#### `TPCQCVis/macro/` — ROOT C++ macros

Compiled and called by the tools for the parts that need the O2/QC C++ stack.

| Macro | Responsibility |
| --- | --- |
| `plotQCData.C` | Core extraction macro: reads the raw QC file and writes the TPC plot objects into `{run}_QC.root` (used by `runPlotter.py`). |
| `getBetheBloch.C` | Returns the Bethe-Bloch fit parameters for a run (used by `downloadFromAlien.py`). |
| `saveRates.C` | Computes the interaction-rate graph and the average/start/mid/end rates (used by the `--add_run_param` path of `runPlotter.py`). |
| `drawDeadChannelMap.C` | Builds the dead-channel-map histograms (used with `--dead_channel_maps`). |
| `makeQCcaldet.C`, `makePadCalibTree.C`, `plotCalDetMap.C`, `ccdbToTree.C`, `getIDCs.C`, … | Detector-calibration and CCDB helper macros used by the expert dashboards/notebooks. |

#### `TPCQCVis/tests/` — tests

`test_core.py` is a runnable `pytest` suite covering the `core/` logic
(path parsing, run selection, poll-trigger parsing, state persistence). Run it
inside the QC environment with `pytest TPCQCVis/tests/test_core.py`. The other
`.ipynb` files in this directory are exploratory notebooks, not automated tests.
 
### Exporting notebooks:
#### As report:
Command to run:
```
jupyter nbconvert myNotebook.ipynb --to html --template classic --no-input --execute
```
> Remove the `--no-input` to have the code also in the report

#### As slides:
Command to run:
```
jupyter nbconvert myNotebook.ipynb --to slides --no-input --SlidesExporter.reveal_scroll=True
```

Then open the html file with text editor and change the initializer of reveal to this:
```
Reveal.initialize({
            controls: true,
            progress: true,
            history: false,
            transition: "slide",
            slideNumber: "true",
            viewDistance: 50,
            mobileViewDistance: 20,
            preloadIframes: true,
            autoPlayMedia:true,
            plugins: [RevealNotes]
        });
```
This makes it possible that all the plots in the slides will be loaded automatically when file is opened on browser. (works on Chrome, still didn't get the expected behavior in Firefox)

### Interactive Dashboards
> [!NOTE]
> It is planned to also provide interactive dashboards generated using RootInteractive for TPC QC. These will be based on skimmed AO2D and reconstructed data, as well as timeseries and aggregated run informations collected from CCDB and QCDB.
> Currently this project is [WIP] and no automatized dashboards are yet being created.

For the development, some example dashboard templates can be found at `/TPCQCVis/dashboards/`

### Full workflow example
You were asked to make all necessary reports for the newly produced LHC23zzk apass3. And the experts are curious how it compares to the previous apass2. Since we only need apass2 for comparison. We will omit generating the standalone reports for that pass, but we will still create the root files needed for the comparison report.

> [!WARNING]
> There is a high chance by the time you are running this, the apass2 or apass3 files for LHC23zzk were outdate and got deleted from alien. In that case, follow these steps for more recent productions. Alternatively, you can also copy the files from our project backup at `/eos/project-a/alice-tpc-qc/data/` accessed via lxplus or CERNBox.
> 
Let's see how to generate necessary reports.
#### Approach 1:  Step-by-Step

This approach runs each pipeline stage by hand, which is the best way to
understand what every script does and how its options change its behaviour. The
four scripts involved are `downloadFromAlien.py` → `runPlotter.py` →
`generateReport.py` → `syncAndUpload.py`.

##### Step 1 — Download the raw QC files (`downloadFromAlien.py`)

We will need the `QC_fullrun.root` files for both apass3 and apass2. They are located in directories `/alice/data/2023/LHC23zzk/` in alien. To download them locally, we make use of the downloadFromAlien.py tool:
```
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2023/LHC23zzk/apass3/ /alice/data/2023/LHC23zzk/ apass3
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2023/LHC23zzk/apass2/ /alice/data/2023/LHC23zzk/ apass2
```
You should end up with two folders containing `.root` files for different runs in `$TPCQCVIS_DATA/2023/LHC23zzk/`.

**Arguments (positional, in order):**
- `local_dir` — where the downloaded `{run}.root` files are written (e.g. `$TPCQCVIS_DATA/2023/LHC23zzk/apass3/`).
- `remote_dir` — the AliEn base directory for the period, `/alice/data/{year}/{period}/`.
- `production` — the pass name (e.g. `apass3`). Used to locate `{run}/{production}/QC/001/QC.root` (falls back to `QC_fullrun.root`) on AliEn.
- `[runList ...]` — *optional* explicit run numbers. If omitted, the run list is discovered automatically with `alien_ls` on `remote_dir`.

**Options:**
- `--dead_channel_maps` / `-dcm` — also fetch and write the per-run **dead channel map** histograms into the downloaded file. Off by default because fetching them is slow.

**What it does under the hood:** for every run it finds the QC object on AliEn, copies it locally (with several retry attempts), and then **enriches each file**: it always appends a `BetheBlochParameters` TTree (computed by the `macro/getBetheBloch.C` macro) and, when `--dead_channel_maps` is given, a `DeadChannelMaps` directory.

##### Step 2 — Extract TPC plots (`runPlotter.py`)

```
python $TPCQCVIS_DIR/TPCQCVis/tools/runPlotter.py -t 10 $TPCQCVIS_DATA/2023/LHC23zzk/apass3/
python $TPCQCVIS_DIR/TPCQCVis/tools/runPlotter.py -t 10 $TPCQCVIS_DATA/2023/LHC23zzk/apass2/
```
Now you should have accompanying `_QC.root` files in your directories.

**Argument:**
- `local_dir` (positional) — directory containing the `{run}.root` files to process. Files that already have a `_QC.root` are skipped unless `--rerun` is given.

**Options:**
- `-t`, `--num_threads` — number of runs to plot in parallel (default: `1`).
- `--rerun` — reprocess runs even if their `_QC.root` already exists (default: skip already-processed runs).
- `--add_run_param` / `--not_add_run_param` — add per-run parameters (**default: on**). This calls `o2-calibration-get-run-parameters` and the `macro/saveRates.C` macro to obtain the interaction rate (average / start / mid / end), magnetic field and run duration, and writes them as a `RunParameters` TTree plus an interaction-rate graph into the `_QC.root`. Use `--not_add_run_param` to skip this (e.g. for quick plotting or when the CCDB/calibration info is unavailable).
- `--excludedPoints` — number of points excluded from the start and end of the run when computing the interaction rate (default: `10`, in units of ~10 s per point). Only relevant with `--add_run_param`.
- `--period_postprocessing` — period-level postprocessing runs **by default** (producing `periodOverview.root` with the aggregated/median distributions used by the period report); passing this flag **turns it off**.
- `--target FILE` — plot a single specific `.root` file instead of scanning `local_dir`.

**What it does under the hood:** loads the compiled `macro/plotQCData.C` macro, extracts the TPC-relevant objects from each raw QC file into a new `{run}_QC.root`, adds moving-window overlay histograms, and (by default) the run parameters and period postprocessing.

##### Step 3 — Generate the HTML reports (`generateReport.py`)

```
python $TPCQCVIS_DIR/TPCQCVis/tools/generateReport.py  $TPCQCVIS_DATA/2023/ LHC23zzk apass3
```
You should end up with multiple `{RunNumber}.html` files, one `LHC23zzk_apass3.html` inside the apass3 directory and one `LHC23zzk_apass3_comparison.html` report in the outer LHC23zzk directory.

**Arguments (positional, in order):**
- `path` — the *year* directory, e.g. `$TPCQCVIS_DATA/2023/`.
- `period` — the period, e.g. `LHC23zzk`.
- `apass` — the pass to report on, e.g. `apass3`.

**Options:**
- `-t`, `--num_threads` — number of run reports to render in parallel (default: `1`).
- `--rerun` — recreate run reports even if the corresponding `.html` already exists under `$TPCQCVIS_REPORT` (default: skip runs whose report already exists).
- `--apass_comparison PASS` — compare against one specific pass (e.g. `apass2`). By default the comparison report is made against **all** other passes present for the period (`All`).
- `--only_comparison` — skip the per-run and period reports and produce only the comparison report.
- `--n_gaussians {2,3,4}` — number of Gaussians used in the pion–electron separation-power fit (default: `2`; `3` = triple Gaussian; `4` = double Gaussian + exponential).

**What it does under the hood:** it fills the notebook templates in `reports/` with the requested period/pass/run and executes them with `jupyter nbconvert --execute`:
- one **run report** per run from `TPC_AQC_Template_Run.ipynb` → `{run}.html`;
- one **period report** (if more than one run) from `TPC_AQC_Template_Period.ipynb` → `{period}_{apass}.html`;
- one **comparison report** (if more than one pass exists for the period) from `TPC_AQC_Template_ComparePasses.ipynb`.

##### Step 4 — Publish to the webpage (`syncAndUpload.py`)

```
python $TPCQCVIS_DIR/TPCQCVis/tools/syncAndUpload.py
```
Now you should see the latest version of your reports on [alice-tpc-qc.web.cern.ch/reports/2023/LHC23zzk/](https://alice-tpc-qc.web.cern.ch/reports/2023/LHC23zzk/).

**Options:** none — the script asks for interactive confirmation, then moves every `*.html` from `$TPCQCVIS_DATA` to `$TPCQCVIS_REPORT` (via `moveFiles.py`), `rsync`s the report directory to the eos project folder, and triggers the web-server refresh (`updateServer.py`). The publishing targets and ssh secret are taken from the optional environment variables listed in [Setting up](#setting-up).

#### Approach 2:  QC Master
1. Run the QC master for apass2 without reports:
    ```
    python $TPCQCVIS_DIR/TPCQCVis/tools/qc_master.py --path $TPCQCVIS_DATA/2023/ --apass apass2 --download --plot LHC23zzk
    ```
2. Run the QC master for apass3 with reports:
    ```
    python $TPCQCVIS_DIR/TPCQCVis/tools/qc_master.py --path $TPCQCVIS_DATA/2023/ --apass apass3 --download --plot --report LHC23zzk
    ```
3. Upload to the webpage:
    ```
    python $TPCQCVIS_DIR/TPCQCVis/tools/syncAndUpload.py
    ```
    Now you should see the latest version of your reports on [alice-tpc-qc.web.cern.ch/reports/2023/LHC23zzk/](https://alice-tpc-qc.web.cern.ch/reports/2023/LHC23zzk/).