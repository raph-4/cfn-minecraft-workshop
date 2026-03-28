# rules/MinecraftServerRules.py
#
# Custom cfn-lint rules for the Minecraft server template.
#
# HOW CUSTOM RULES WORK:
#   cfn-lint loads Python files from a rules directory and runs them against
#   the template alongside its built-in checks. Each rule is a class that
#   inherits from CloudFormationLintRule and implements a match() method.
#   If match() returns a list of RuleMatch objects, those are reported as
#   errors or warnings in the lint output.
#
# HOW TO RUN LOCALLY:
#   cfn-lint minecraft-server.yaml --append-rules rules/
#
# RULE ID FORMAT:
#   AWS reserves E0000-E9999 for built-in rules. Custom rules should use
#   a prefix that won't clash — we use E9001, E9002 etc. here.

from cfnlint.rules import CloudFormationLintRule, RuleMatch


class ServerJarUrlRequired(CloudFormationLintRule):
    """
    Ensures ServerJarUrl has been set to an actual URL.
    The parameter has no Default, so CloudFormation will catch a truly missing
    value at deploy time — but this catches the case where someone sets it to
    a placeholder like 'https://example.com' or leaves it as an empty string.
    """
    id          = 'E9001'
    shortdesc   = 'ServerJarUrl must be a valid HTTPS URL'
    description = 'ServerJarUrl must start with https:// and not be a placeholder'
    tags        = ['parameters']

    def match(self, cfn):
        matches = []

        url = (
            cfn.template
               .get('Parameters', {})
               .get('ServerJarUrl', {})
               .get('Default', None)
        )

        if url is not None:
            if not url.startswith('https://'):
                matches.append(RuleMatch(
                    ['Parameters', 'ServerJarUrl', 'Default'],
                    'ServerJarUrl must start with https://'
                ))
            placeholders = ['example.com', 'your-url-here', 'TODO', 'placeholder']
            if url == '' or any(p in url.lower() for p in placeholders):
                matches.append(RuleMatch(
                    ['Parameters', 'ServerJarUrl', 'Default'],
                    'ServerJarUrl looks like a placeholder — set it to a real JAR download URL'
                ))

        return matches


class SshCidrNotWideOpen(CloudFormationLintRule):
    """
    Warns when AllowSshCidr is left as 0.0.0.0/0 (open to the entire internet).
    This is a WARNING rather than an error — it's valid for a workshop where
    you don't know the student's IP, but should be flagged for real deployments.
    """
    id          = 'W9001'
    shortdesc   = 'AllowSshCidr is open to the world'
    description = (
        'AllowSshCidr is set to 0.0.0.0/0, which allows SSH from any IP. '
        'For real deployments, restrict this to your own IP (e.g. 1.2.3.4/32).'
    )
    tags        = ['parameters', 'security']

    def match(self, cfn):
        matches = []

        cidr = (
            cfn.template
               .get('Parameters', {})
               .get('AllowSshCidr', {})
               .get('Default', None)
        )

        if cidr == '0.0.0.0/0':
            matches.append(RuleMatch(
                ['Parameters', 'AllowSshCidr', 'Default'],
                'AllowSshCidr is 0.0.0.0/0 — restrict to your IP for real deployments'
            ))

        return matches


class JavaRamSanityCheck(CloudFormationLintRule):
    """
    Checks that JavaMaxRam is not set higher than what the chosen instance can handle.
    """
    id          = 'E9002'
    shortdesc   = 'JavaMaxRam too high for selected instance type'
    description = (
        'JavaMaxRam should leave at least 512 MB for the OS. '
        'On a t4g.small (2 GB), do not exceed 1536M.'
    )
    tags        = ['parameters']

    INSTANCE_RAM_MB = {
        't4g.small':  2048,
        't4g.medium': 4096,
        't4g.large':  8192,
        'm7g.medium': 4096,
        'm7g.large':  8192,
    }
    OS_OVERHEAD_MB = 512

    def _parse_ram(self, value: str):
        value = value.strip()
        if value.endswith('G') or value.endswith('g'):
            return int(value[:-1]) * 1024
        if value.endswith('M') or value.endswith('m'):
            return int(value[:-1])
        return None

    def match(self, cfn):
        matches = []
        params = cfn.template.get('Parameters', {})

        max_ram_str   = params.get('JavaMaxRam',   {}).get('Default', '1300M')
        instance_type = params.get('InstanceType', {}).get('Default', 't4g.small')

        max_ram_mb      = self._parse_ram(max_ram_str)
        instance_ram_mb = self.INSTANCE_RAM_MB.get(instance_type)

        if max_ram_mb and instance_ram_mb:
            usable = instance_ram_mb - self.OS_OVERHEAD_MB
            if max_ram_mb > usable:
                matches.append(RuleMatch(
                    ['Parameters', 'JavaMaxRam', 'Default'],
                    (
                        f'JavaMaxRam ({max_ram_str}) exceeds usable RAM for {instance_type}. '
                        f'Max recommended: {usable}M (total {instance_ram_mb}M minus {self.OS_OVERHEAD_MB}M OS overhead)'
                    )
                ))

        return matches


class EbsVolumeTooSmall(CloudFormationLintRule):
    """
    Warns if EbsVolumeSize is set below 10 GB.
    """
    id          = 'W9002'
    shortdesc   = 'EbsVolumeSize may be too small'
    description = 'EbsVolumeSize below 10 GB leaves very little space for worlds and plugins'
    tags        = ['parameters']

    def match(self, cfn):
        matches = []

        size = (
            cfn.template
               .get('Parameters', {})
               .get('EbsVolumeSize', {})
               .get('Default', 20)
        )

        try:
            if int(size) < 10:
                matches.append(RuleMatch(
                    ['Parameters', 'EbsVolumeSize', 'Default'],
                    f'EbsVolumeSize is {size} GB — recommended minimum is 10 GB'
                ))
        except (ValueError, TypeError):
            pass

        return matches
