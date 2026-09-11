const { withDangerousMod } = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

const withGradleVersion = (config, { version }) => {
  return withDangerousMod(config, [
    "android",
    async (config) => {
      const wrapperPath = path.join(
        config.modRequest.platformProjectRoot,
        "gradle/wrapper/gradle-wrapper.properties",
      );
      const contents = fs.readFileSync(wrapperPath, "utf8");
      const next = contents.replace(
        /distributionUrl=.*$/m,
        `distributionUrl=https\\://services.gradle.org/distributions/gradle-${version}-bin.zip`,
      );
      fs.writeFileSync(wrapperPath, next);
      return config;
    },
  ]);
};

module.exports = withGradleVersion;
