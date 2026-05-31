import React from 'react';
import { Download } from 'lucide-react';

interface CsvExportButtonProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any[];
    filename?: string;
}

export const CsvExportButton: React.FC<CsvExportButtonProps> = ({ data, filename = 'sessions_export.csv' }) => {
    const handleExport = () => {
        if (!data || data.length === 0) return;

        // Extract headers from the first object
        const headers = Object.keys(data[0]).filter(k => typeof data[0][k] !== 'object');
        const csvRows = [];

        // Add header row
        csvRows.push(headers.join(','));

        // Add data rows
        for (const row of data) {
            const values = headers.map(header => {
                const val = row[header];
                if (val !== null && val !== undefined) {
                    const strVal = String(val);
                    // Quote strings that contain commas or newlines
                    if (strVal.includes(',') || strVal.includes('\n') || strVal.includes('"')) {
                        return `"${strVal.replace(/"/g, '""')}"`;
                    }
                    return strVal;
                }
                return '';
            });
            csvRows.push(values.join(','));
        }

        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <button
            onClick={handleExport}
            className="glass-btn flex items-center gap-2 text-xs"
            title="Export to CSV"
        >
            <Download size={14} /> Export CSV
        </button>
    );
};

export default CsvExportButton;
