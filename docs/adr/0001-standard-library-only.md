# Use the Python standard library only and drive git through subprocess

cgwt has no runtime dependency. Every git operation runs through one `run_git` function that calls `subprocess`, so tests have one seam to mock and git porcelain output is the only interface cgwt parses. A dependency needs a stated reason, because cgwt must stay a single Python package that installs anywhere Python and git exist.
