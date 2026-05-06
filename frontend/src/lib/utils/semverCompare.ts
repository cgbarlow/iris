/**
 * v5.5.0 (issue #48): tiny semver comparator used by the extension
 * manager UI to decide whether an "Update available" pill should
 * render. Tolerant of `v` prefixes and prerelease/metadata suffixes —
 * we only compare the numeric x.y.z prefix.
 */

function parts(version: string): number[] {
	const stripped = version.replace(/^v/i, '');
	const out: number[] = [];
	for (const chunk of stripped.split('.')) {
		let num = '';
		for (const c of chunk) {
			if (c >= '0' && c <= '9') num += c;
			else break;
		}
		out.push(num.length ? parseInt(num, 10) : 0);
	}
	return out;
}

/** Returns true iff `latest` is a strictly newer version than `installed`. */
export function isNewerSemver(latest: string | null | undefined, installed: string | null | undefined): boolean {
	if (!latest || !installed) return false;
	const a = parts(latest);
	const b = parts(installed);
	const len = Math.max(a.length, b.length);
	for (let i = 0; i < len; i++) {
		const ai = a[i] ?? 0;
		const bi = b[i] ?? 0;
		if (ai > bi) return true;
		if (ai < bi) return false;
	}
	return false;
}
