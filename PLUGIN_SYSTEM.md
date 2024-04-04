The general idea of the plugin system will be as such:
- Most basic features, including challenges and other types of updates, will add support for chained callbacks.
- These chained callbacks will be able to
    - Edit the data returned by the original function
    - Replace the data returned by the original function
    - Prevent the original function from returning anything
    - Append new data to the originally returned data
- These chained callbacks will need to be registered by plugins, but doing them in this way allows for
    - Unlimited amount of callbacks for each plugin
    - Easy performance troubleshooting, as you only need to measure the individual performance of each plugin
    - No limit to the retrieved data

All data that will be *ADDED* will be found under the `extensions` dict, organized as, for example:
- Users
    - name
    - id
    - ...
    - extensions
        - PLUGIN_NAME
            - whatever the hell you want

This will both allow for infinitely extensible objects, and should prevent conflicts between fields
Doing it this way also allows for collaboration between plugins.

Indeed, another addition will be the plugin loading order, which will consist of:
- Each plugin can depend on another plugin by calling `required_dependency("plugin_name")` (can also have optional dependencies with `optional_dependency("plugin_name")`)
    - This function returns True if the plugin loads, False if it fails (only if optional=True, otherwise it exits)
- When this function is called, the current plugin is marked as "building dependencies"
- The next plugin is then loaded, which can, in turn, depend on other plugins
- If this plugin is attempted to be loaded while it's building dependencies, we have a dependency loop, FATAL error, exit
- If the plugin is depended upon after it's been initialized, skip initialization and return OK

Since plugins have a guaranteed load order (at least after plugin_name), plugins can now cooperate by passing data to eachother via reading other plugins' `extensions` field.
Collaboration within plugin is not defined otherwise, and is to be defined by plugin authors

Other features that do not override anything, but instead, extend a system will move to a system much like the current CHALLENGE_TYPES one, a field that a plugin can register itself with.

CHALLENGE_TYPES and FLAG_TYPES will be moved to be internal, as, currently, they are the only dependencies that the **INTERNAL** code has on real plugin code (the init and the migration folder are both fair game)

Such systems will be:
- CHALLENGE_TYPES
- FLAG_TYPES
- OAUTH_PROVIDER
- FILE_PROVIDER

Types and providers will be given as options when applicable