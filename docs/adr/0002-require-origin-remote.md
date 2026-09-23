# Every command requires an origin remote

The project identifier and name derive from the URL of `origin`, the default base is `origin/HEAD`, and the safety checks compare against `origin/HEAD`. A repository without `origin` has no project identity and no reference for safety, so every cgwt command fails with one error on it. A remote under another name does not count.
