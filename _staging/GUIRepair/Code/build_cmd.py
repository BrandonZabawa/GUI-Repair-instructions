def make_check_cmd(instance_repo_path):
    if "bpmn-js" in instance_repo_path:
        # build_cmd = 'pnpm install & pnpm run distro'
        build_cmd = "ls"
    elif "GoogleChrome__lighthouse" in instance_repo_path:
        # must use npm install
        build_cmd = "ls"
    elif "scratch-gui" in instance_repo_path:
        # must use npm install, you need use npm start to open browser
        # build_cmd = 'export NODE_OPTIONS=--openssl-legacy-provider && npm start'
        build_cmd = "ls"
    elif "openlayers" in instance_repo_path:
        # build_cmd = 'export NODE_OPTIONS=--openssl-legacy-provider && pnpm run build-legacy'
        build_cmd = "ls"
    elif "alibaba-fusion" in instance_repo_path:
        # must use old version node, such as "fnm use 14"
        build_cmd = "ls"

    elif "carbon-design-system" in instance_repo_path:
        # must use yarn install, then yarn add file:../carbon/packages/react in you web project
        # build_cmd = 'yarn build'

        # check errors
        build_cmd = "yarn run lint"
    elif "grommet" in instance_repo_path:
        # must use yarn install, then yarn add file:../carbon/packages/react in you web project
        build_cmd = "yarn install && export NODE_OPTIONS=--openssl-legacy-provider && yarn run lint"
        # build_cmd = 'ls'
    elif "prettier" in instance_repo_path:
        # must use yarn install
        build_cmd = "yarn run lint"

    elif "prism" in instance_repo_path:
        # must use npm install
        # build_cmd = 'npm run lint'
        build_cmd = "ls"

    elif "highlightjs" in instance_repo_path:
        build_cmd = "ls"

    else:
        build_cmd = "ls"

    return build_cmd


def make_build_cmd(instance_repo_path):
    if "bpmn-js" in instance_repo_path:
        # build_cmd = 'pnpm install & pnpm run distro'
        build_cmd = "ls"
    elif "GoogleChrome__lighthouse" in instance_repo_path:
        # must use npm install
        # yarn
        # yarn build-all
        build_cmd = "ls"
    elif "scratch-gui" in instance_repo_path:
        # must use npm install, you need use npm start to open browser
        build_cmd = "export NODE_OPTIONS=--openssl-legacy-provider && npm start"
    elif "openlayers" in instance_repo_path:
        build_cmd = (
            "export NODE_OPTIONS=--openssl-legacy-provider && pnpm run build-legacy"
        )
    elif "alibaba-fusion" in instance_repo_path:
        # must use old version node, such as "fnm use 14/12/10"
        # npm install node-sass@4.14.1 --save-dev
        build_cmd = "ls"

        if "alibaba-fusion__next-4859" in instance_repo_path:
            build_cmd = "fnm use 14 && npm run build:dist"
        if "alibaba-fusion__next-4182" in instance_repo_path:
            build_cmd = "fnm use 14 && npm run build && npm run pack"
        if "alibaba-fusion__next-2984" in instance_repo_path:
            build_cmd = "fnm use 12 && npm run build && npm run pack"
        if "alibaba-fusion__next-2860" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-2131" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-1708" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-1500" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-1509" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-966" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-877" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-895" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-717" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"
        if "alibaba-fusion__next-94" in instance_repo_path:
            build_cmd = "fnm use 10 && npm run build && npm run pack"

        # build_cmd = 'export NODE_OPTIONS=--openssl-legacy-provider && pnpm run pack'
    elif "carbon-design-system" in instance_repo_path:
        # Note that different repo version need different Node version, use "fnm install xx", then "fnm use xx" to change the Node version
        # "npm install -g yarn", must use "yarn install", "yarn build", then "cd react/packages" run "yarn storybook" to open the dev demo

        # Note that carbon only run build one time, then we only need to update the code
        build_cmd = "fnm use 22 && yarn build"

        if "carbon-design-system__carbon-3118" in instance_repo_path:
            # build_cmd = 'fnm use 10 && yarn build'
            build_cmd = "ls"
        if "carbon-design-system__carbon-3139" in instance_repo_path:
            # build_cmd = 'fnm use 10 && yarn build'
            build_cmd = "ls"
        if "carbon-design-system__carbon-4167" in instance_repo_path:
            build_cmd = "fnm use 10 && yarn build"
        if "carbon-design-system__carbon-4347" in instance_repo_path:
            build_cmd = "fnm use 10 && yarn build"
        if "carbon-design-system__carbon-4816" in instance_repo_path:
            build_cmd = "fnm use 10 && yarn build"
        if "carbon-design-system__carbon-5156" in instance_repo_path:
            build_cmd = "fnm use 10 && yarn build"
        if "carbon-design-system__carbon-6906" in instance_repo_path:
            build_cmd = "fnm use 12 && yarn build"
        if "carbon-design-system__carbon-6964" in instance_repo_path:
            build_cmd = "fnm use 12 && yarn build"
        if "carbon-design-system__carbon-11664" in instance_repo_path:
            # build_cmd = 'fnm use 16 && yarn build'
            build_cmd = "ls"
        if "carbon-design-system__carbon-12332" in instance_repo_path:
            build_cmd = "fnm use 16 && yarn build"
            # build_cmd = 'ls'

        if "carbon-design-system__carbon-15197" in instance_repo_path:
            # build_cmd = 'fnm use 16 && yarn build'
            build_cmd = "ls"
        if "carbon-design-system__carbon-16237" in instance_repo_path:
            # build_cmd = 'fnm use 18 && yarn build'
            build_cmd = "ls"
        # check errors
        if "carbon-design-system__carbon-9136" in instance_repo_path:
            build_cmd = "ls"

        # build_cmd = 'ls'
    elif "grommet" in instance_repo_path:
        # must use yarn install, then yarn add file:../carbon/packages/react in you web project
        # build_cmd = 'yarn install && export NODE_OPTIONS=--openssl-legacy-provider && yarn run build'
        build_cmd = "ls"
    elif "prettier" in instance_repo_path:
        # must use yarn install, also can use "yarn run lint" to check code format
        build_cmd = "yarn run build"

        if "prettier__prettier-11884" in instance_repo_path:
            build_cmd = (
                "fnm use 22 && NODE_OPTIONS=--openssl-legacy-provider yarn run build"
            )
        if "prettier__prettier-9866" in instance_repo_path:
            build_cmd = (
                "fnm use 22 && NODE_OPTIONS=--openssl-legacy-provider yarn run build"
            )
        if "prettier__prettier-8536" in instance_repo_path:
            build_cmd = (
                "fnm use 22 && NODE_OPTIONS=--openssl-legacy-provider yarn run build"
            )
        if "prettier__prettier-6319" in instance_repo_path:
            build_cmd = (
                "fnm use 22 && NODE_OPTIONS=--openssl-legacy-provider yarn run build"
            )
        if "prettier__prettier-4202" in instance_repo_path:
            build_cmd = (
                "fnm use 22 && NODE_OPTIONS=--openssl-legacy-provider npm run build"
            )

    elif "prism" in instance_repo_path:
        # must use npm install
        build_cmd = "npm run build"

        # don't need build, because only import the source file is enough
        if "PrismJS__prism-1500" in instance_repo_path:
            build_cmd = "npm run test"
        if "PrismJS__prism-1572" in instance_repo_path:
            build_cmd = "npm run test"
        if "PrismJS__prism-1573" in instance_repo_path:
            build_cmd = "npm run test"
        if "PrismJS__prism-1585" in instance_repo_path:
            build_cmd = "npm run test"
        if "PrismJS__prism-1602" in instance_repo_path:
            build_cmd = "npm run test"
        if "PrismJS__prism-1747" in instance_repo_path:
            build_cmd = "npm run test"

    elif "highlightjs" in instance_repo_path:
        build_cmd = "pnpm run build-browser"

        # must use npm install
        if "highlight.js-2684" in instance_repo_path:
            build_cmd = "node tools/build.js -n bash"
        if "highlight.js-2703" in instance_repo_path:
            build_cmd = "node tools/build.js -n scala"
        if "highlight.js-2704" in instance_repo_path:
            build_cmd = "node tools/build.js -n fsharp"
        if "highlight.js-2726" in instance_repo_path:
            build_cmd = "node tools/build.js -n latex"
        if "highlight.js-2740" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2750" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2765" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2785" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2811" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2897" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2899" in instance_repo_path:
            build_cmd = "node tools/build.js -n dart"
        if "highlight.js-2927" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2932" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2960" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-2972" in instance_repo_path:
            build_cmd = "npm run build-browser"
        if "highlight.js-3000" in instance_repo_path:
            build_cmd = "npm run build-browser"

        # must use pnpm install
        if "highlight.js-3154" in instance_repo_path:
            build_cmd = "node tools/build.js -n ruby"
        if "highlight.js-3203" in instance_repo_path:
            build_cmd = "node tools/build.js -n powershell"
        if "highlight.js-3207" in instance_repo_path:
            build_cmd = "node tools/build.js -n elixir"
        if "highlight.js-3212" in instance_repo_path:
            build_cmd = "node tools/build.js -n elixir"
        if "highlight.js-3249" in instance_repo_path:
            build_cmd = "node tools/build.js -n latex"
        if "highlight.js-3278" in instance_repo_path:
            build_cmd = "node tools/build.js -n typescript"
        if "highlight.js-3287" in instance_repo_path:
            build_cmd = "node tools/build.js -n verilog"
        if "highlight.js-3301" in instance_repo_path:
            build_cmd = "node tools/build.js -n css"
        if "highlight.js-3316" in instance_repo_path:
            build_cmd = "node tools/build.js -n cpp c"
        if "highlight.js-3367" in instance_repo_path:
            build_cmd = "node tools/build.js -n python"
        if "highlight.js-3411" in instance_repo_path:
            build_cmd = "node tools/build.js -n typescript javascript"
        if "highlight.js-3457" in instance_repo_path:
            build_cmd = "node tools/build.js -n xml markdown"

        if "highlight.js-3644" in instance_repo_path:
            build_cmd = "node tools/build.js -n cmake"

    else:
        build_cmd = "ls"

    return build_cmd
