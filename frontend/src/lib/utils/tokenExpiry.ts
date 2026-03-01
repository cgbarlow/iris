/**
 * Parse JWT token expiry time.
 *
 * Extracts the `exp` claim from a JWT and returns it as a millisecond timestamp.
 * Used by SessionTimeoutWarning to schedule the warning timer.
 *
 * @param token - JWT access token string, or null
 * @returns Expiry time in milliseconds since epoch, or null if the token is invalid
 */
export function parseTokenExpiry(token: string | null): number | null {
	if (!token) return null;

	try {
		const parts = token.split('.');
		if (parts.length !== 3) return null;

		const payload = JSON.parse(atob(parts[1]));
		if (typeof payload.exp !== 'number') return null;

		return payload.exp * 1000;
	} catch {
		return null;
	}
}
