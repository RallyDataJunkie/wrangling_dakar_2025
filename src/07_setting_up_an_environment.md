# Setting Up Your Development Environment

One of the ways you can use this book, or guide, or whatver it is, is as a practical hands on guide to working with data at the code level as well as at an "application" level.

If you want to gain experience of working with data at the code level, you'll need access to some sort of development environment. For working at the application level, all the applications introduced in this guide can be found online, although you can also run them locally if you prefer.

The quickest way to get started with code is to access it via a __JupyterLite__ site set up to support this book. You can find one such site at: https://rallydatajunkie.com/wrangling_dakar_2025

JupyterLite provides an interactive *JupyterLab* development environment that runs purely within the browser. You can work with the provided Jupyter notebooks within this environment:

- access files from the file browser on the left hand side;
- notebook files contain markdown/text cells, code cells and may also display code cell outputs;
  - click in a code cell or double click in a markdown cell to edit it;
  - click the toolbar play button or `shift-enter` to "run" a code cell (that is, execute the code in the cell) or "render" a markdown cell.

The JupyterLite environment executes the notebook Python code using a code interpreter loaded into your browser.

Another "ready-to-run" approach is to use a customised `devcontainer` environment within a *VS Code* editor or via GitHub Codespaces.

- if you have a GitHub account, you can access CodeSpaces free for up to 60 hours a month; to launch a preconfigured CodeSpace defined for use with this guide, visit https://github.com/RallyDataJunkie/wrangling_dakar_2025, click on the green *Code* menu button, select the *Codespaces* tab and launch a Codespace. By default, this will launch a customised environment into a VS Code editor. having created your codespace, from your repository Codespaces tab, you can click the "more actions" three dots (...) for a Codespace and open the environment into a JupyterLab user interface if you prefer.

You can also run a devcontainer locally on your own computer if you have Docker installed. The devcontainer configuration file can be found in the `RallyDataJunkie/wrangling_dakar_2025` GitHiub repository.