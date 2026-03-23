/**
 * Reactive localStorage-backed store for the "show element count" user preference.
 */

let _showElementCount = $state(
	typeof localStorage !== 'undefined'
		? localStorage.getItem('iris-show-element-count') !== 'false'
		: true,
);

export function getShowElementCount(): boolean {
	return _showElementCount;
}

export function setShowElementCount(value: boolean): void {
	_showElementCount = value;
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem('iris-show-element-count', String(value));
	}
}
