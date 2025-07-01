# Contributing to Streamlink

Want to get involved? Thanks! There are plenty of ways to help!


## Reporting issues

A bug is a *demonstrable problem* that is caused by the **latest version** of the code in the repository. Good bug reports are extremely helpful - thank you!

Please read the following guidelines before you [report an issue][issues]:

1. **Use the GitHub issue search**

   Check if the issue has already been reported. If it has been and is still unresolved, then please comment on the existing issue.

   Please avoid comments like "+1", "me too", etc., as they don't contribute to solving the issue and instead unnecessarily notify users subscribed to the issue or activities of the entire repository. Instead, use GitHub's notification feature on specific issues or pull requests via the sidebar on the right in order to receive status updates, or click the watch button at the top.

2. **Check if the issue has been resolved**

   The `master` branch may already contain a fix, so please have a look at the recent commit history first. Don't comment on commits and instead open a new thread on the issue tracker if you have found a mistake in a code commit.

   Resolved issues or merged pull requests should never be commented on and a new issue should be opened if something is still not working or has stopped working again. But before opening a new issue, check that you are indeed using the latest stable or development version.

3. **Isolate the demonstrable problem**

   Make sure that the code in the project's repository is *definitely* responsible for the issue by excluding external factors which may influence the results.

   These external factors can be specific configurations in the used environment, the connection to a specific website or streaming service, the usage of VPNs or proxy servers, and many other things. Please keep that in mind when reporting issues.

   The project maintainers must be able to reproduce the issue you're trying to report, which is the reason why **a full debug log is required** when reporting plugin issues or general bugs, as it includes important information about the environment Streamlink is run in.

4. **Format your issue report**

   [Well formatted texts][mastering-markdown] will make it much easier for developers to understand your report.

   Please at the very least put your (additional) log output or code snippets into markdown code-blocks (surrounded by triple backticks - see the link above).

   The various issue templates will aid you in structuring your report when submitting a new issue. Thank you!


## Feature requests

Feature requests are welcome, but take a moment to find out whether your idea fits with the scope and aims of the project. It's up to *you* to make a strong case to convince the project's developers of the merits of this feature. Please provide as much detail and context as possible.


## Plugin requests

Plugin submissions and requests are a great way to improve Streamlink. Requests should be as detailed as possible and dedicated to only a single streaming website/service.

Information about the website, as well as explicit URLs from your web browser's URL address bar are required, as are details regarding the website, what it is, who it is run by, and more. This allows for easier plugin review and implementation. We reserve the right to refuse to implement, develop, or update any plugin. In addition, we may remove existing plugins at our own discretion at any time without explanation.

Before you request a plugin, please be aware that this will merely be a suggestion for the project maintainers (or anyone else) to have a look at the website and implement a new plugin for it. In the vast majority of cases, no one except you will initially have an interest in such a plugin, so you should think about whether it will be useful for other users of Streamlink.

Implementing new plugins can be a lot of effort, as well as keeping them maintained. Providing plugin code in a pull request written on your own after it has been discussed and approved in the request issue is therefore much appreciated, if the code quality is acceptable. Further assistance in plugin maintenance via plugin issues or bugfix pull requests will be greatly appreciated as well.

Please remember that custom plugins can always be [sideloaded][plugin-sideloading], in case your request will be rejected or if plugins will be removed from Streamlink's `master` branch.

**Plugins which fall under the following categories will not be implemented and any requests will be rejected.** Depending on the case, already existing plugins which don't meet these plugin criteria, may be kept.


### Plugin rules

1. **Any kind of streaming service that uses DRM protection**

    Streamlink won't implement or break any DRM schemes.

2. **Sites which are hosting stolen content as their main source of content**

    Plugins must only support websites with authentic content.

3. **Sites which are primarily rehosting content**

    Plugins must only implement the original/primary website where the content is hosted or shown.

4. **Sites which require paid logins or subscriptions**

    Plugin implementations and maintenance must be possible by everyone. Paid access prevents this.

5. **NSFW sites of a pornographic nature**

    This also includes borderline NSFW content, as it lowers the bar for follow-up plugin requests.

6. **Sites which don't provide any real live-streaming content**

    For example VOD-only content or VODs being re-broadcasted.

7. **Sites which don't provide any video streaming content**

    For example radio stations or streams where the primary focus is the audio content.

8. **Sites where the maintainer has requested we don't add their site to Streamlink**

    We respect legitimate requests by the owners of certain websites, depending on their size.

9. **Sites which are unmaintained, are in beta or are undergoing heavy amounts of development and may change rapidly**

    Stability of new plugin implementations must be guaranteed.

10. **Sites which have no way to determine viewership numbers**

    Plugins must not implement websites which are unused or which only have a handful of real/actual users.

11. **Sites which are static cameras of a physical location**

    We don't consider plugin implementations for this kind of content to be useful.


## Pull requests

Good pull requests - patches, improvements, and new features - are a fantastic help. They should remain focused in scope and avoid containing unrelated commits.

**Please ask first** before embarking on any significant pull request, for example:

- implementing features
- adding new plugins
- refactoring code

Otherwise, you risk spending a lot of time working on something that the project's developers might not want to merge into the project.

Please adhere to the coding conventions used throughout a project (i.e. indentation, white space, accurate comments) and any other requirements, such as test coverage.

Adhering to the following process is the best way to get your work included in the project:

1. [Fork][howto-fork] the project, clone your fork, and configure the remotes:
   ```bash
   git clone git@github.com:YOUR-USERNAME/streamlink.git
   cd streamlink
   git remote add upstream https://github.com/streamlink/streamlink.git
   ```

2. If you cloned a while ago, get the latest changes from upstream:
   ```bash
   git checkout master
   git pull upstream master
   ```

3. Create a new topic branch (off the main project branch) to contain your feature, change, or fix:
   ```bash
   git checkout -b TOPIC-BRANCH-NAME
   ```

4. Commit your changes in logical chunks. Please adhere to these [git commit message guidelines][howto-format-commits] or your code is unlikely be merged into the project. Use git's [interactive rebase][howto-rebase] feature to tidy up your commits before making them public.

5. If your topic branch is based off an outdated commit on the master branch, then rebase first:
   ```bash
   git checkout master
   git pull upstream master
   git checkout TOPIC-BRANCH-NAME
   git rebase --interactive master
   ```

6. Push your topic branch up to your fork:
   ```bash
   git push origin TOPIC-BRANCH-NAME
   ```

7. [Open a Pull Request][howto-open-pull-requests] with a clear title and description.

8. After rebasing or making amending commits, force-push the branch to your fork:
   ```bash
   git rebase --interactive master
   git push --force origin TOPIC-BRANCH-NAME
   ```

**IMPORTANT**: By submitting a patch, you agree to allow the project owners to license your work
under the terms of the [BSD 2-clause license][license].


## Pull request feedback

Please don't hesitate to provide feedback after a pull request was submitted which will close/resolve an issue you've opened or which you've been following. Depending on the kind of issue the pull request will solve, additional feedback from users is important. This feedback can either be a comment, a simple code review, or better, a validation of all the changes by installing and running Streamlink from the pull request's branch and [providing a full debug log][debug-log].

### Sideloading plugin changes

If the pull request is just about a plugin fix or a new plugin inclusion **without additional changes to Streamlink's codebase**, then the new plugin file can be [sideloaded][plugin-sideloading] **when running the latest stable release version of Streamlink**. However, if the pull request is based on changes that have been made to Streamlink's master branch since the latest stable release, then an installation from the pull request's own git branch or Streamlink's master branch will be necessary.

Preview builds from Streamlink's **master branch** are available [on Windows][preview-builds-windows] as well as on [Linux (via AppImages)][preview-builds-linux].

In case sideloading is possible, simply download the pull request's plugin changes using your web browser from GitHub's pull request interface: "Files changed" tab at the top -> breadcrumbs button of the specific plugin file ("...") -> "View raw". Then download the file into the directory described by the [plugin sideloading documentation][plugin-sideloading].

When sideloaded correctly, a log message will be shown:
```
[session][debug] Plugin XYZ is being overridden by path/to/custom/plugin.py
```

### Installing Streamlink from a pull request's branch

This is the preferred way, to ensure that no side effects arise, but it requires a bit more effort.

First, make sure that you have set up [Git][Git] on your system, as well as a working Python environment that matches the [Python version requirements][python-version] of Streamlink.

Then [create and activate a virtual environment][python-venv] where Streamlink can be installed into, without causing incompatibilities with other packages in your main Python environment.

```bash
# 1. Create a new virtual environment.
python -m venv "PATH/TO/NEW/VENV"

# 2. Run the environment's "activate" shell-script.
#    No file name extension for POSIX compliant shells,
#    .fish for FISH, .ps1 for PowerShell, .bat for Windows Batch, etc.
#
# non-Windows: subdirectory is /bin
source "PATH/TO/NEW/VENV/bin/activate"
# Windows: subdirectory is \Script
"PATH\TO\NEW\VENV\Script\activate.ps1"
```

After that's done, either install Streamlink by cloning its git repository and fetching + checking out the pull request branch, or by using pip to install from the pull request's git branch directly.

```bash
# via git (further code modifications are simple)
git clone https://github.com/streamlink/streamlink
cd streamlink
# upgrade to the latest version of pip
python -m pip install -U pip
# install in "editable mode", including required development dependencies
# (changes to the code are picked up automatically)
python -m pip install -U --upgrade-strategy=eager -e . --group all
# fetch and checkout pull request branch
git fetch --force origin "refs/pull/PULL-REQUEST-ID/head:LOCAL-BRANCH-NAME"
git checkout "LOCAL-BRANCH-NAME"
```

```bash
# via pip (whole install needs to be done on each follow-up code change)
python -m pip install "git+https://github.com/streamlink/streamlink@refs/pull/PULL-REQUEST-ID/head"
```

```bash
# validate install (version string includes git commit ID)
streamlink --loglevel=debug
```


## Acknowledgements

This contributing guide has been adapted from [HTML5 boilerplate's guide][ref-h5bp].


  [issues]: https://github.com/streamlink/streamlink/issues
  [mastering-markdown]: https://guides.github.com/features/mastering-markdown
  [howto-fork]: https://help.github.com/articles/fork-a-repo
  [howto-rebase]: https://help.github.com/articles/interactive-rebase
  [howto-format-commits]: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
  [howto-open-pull-requests]: https://help.github.com/articles/using-pull-requests
  [Git]: https://git-scm.com
  [license]: https://github.com/streamlink/streamlink/blob/master/LICENSE
  [debug-log]: https://streamlink.github.io/latest/cli.html#cmdoption-loglevel
  [plugin-sideloading]: https://streamlink.github.io/latest/cli/plugin-sideloading.html
  [preview-builds-windows]: https://streamlink.github.io/latest/install.html#windows-binaries
  [preview-builds-linux]: https://streamlink.github.io/latest/install.html#linux-appimages
  [python-version]: https://streamlink.github.io/latest/install.html#dependencies
  [python-venv]: https://streamlink.github.io/latest/install.html#virtual-environment
  [ref-h5bp]: https://github.com/h5bp/html5-boilerplate/blob/master/CONTRIBUTING.md
