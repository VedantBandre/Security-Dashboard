import { useEffect, useState } from 'react';

export default function usePolling(fetchData, initialData) {
    const [state, setState] = useState({
        data: initialData,
        loading: true,
        error: null,
        lastRefresh: null,
    });
    const [refreshCount, setRefreshCount] = useState(0);

    useEffect(() => {
        let active = true;
        let pending = false;

        function load() {
            if (pending) return;
            pending = true;
            Promise.resolve().then(fetchData).then((data) => {
                if (active) {
                    setState({ data, loading: false, error: null, lastRefresh: new Date() });
                }
            }).catch((error) => {
                if (active) {
                    setState((previous) => ({ ...previous, loading: false, error: error.message }));
                }
            }).finally(() => {
                pending = false;
            });
        }

        load();
        const id = setInterval(load, 5000);
        return () => {
            active = false;
            clearInterval(id);
        };
    }, [fetchData, refreshCount]);

    return { ...state, refresh: () => setRefreshCount((count) => count + 1) };
}
