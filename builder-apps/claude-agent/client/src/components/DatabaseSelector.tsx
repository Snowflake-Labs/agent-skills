import React, { useState, useEffect } from 'react';
import type { DatabaseInfo, SchemaInfo } from '../types/agent';
import { fetchSchemas } from '../services/api';

interface Props {
  databases: DatabaseInfo[];
  loading: boolean;
  selectedDatabase: string | null;
  selectedSchema: string | null;
  onSelect: (database: string | null, schema: string | null) => void;
}

export function DatabaseSelector({
  databases,
  loading,
  selectedDatabase,
  selectedSchema,
  onSelect,
}: Props) {
  const [schemas, setSchemas] = useState<SchemaInfo[]>([]);
  const [schemasLoading, setSchemasLoading] = useState(false);

  // Fetch schemas when database changes
  useEffect(() => {
    if (!selectedDatabase) {
      setSchemas([]);
      return;
    }
    setSchemasLoading(true);
    fetchSchemas(selectedDatabase)
      .then(setSchemas)
      .catch((err) => {
        console.error('Failed to load schemas:', err);
        setSchemas([]);
      })
      .finally(() => setSchemasLoading(false));
  }, [selectedDatabase]);

  return (
    <div className="database-selector">
      <label>Database</label>
      <select
        value={selectedDatabase || ''}
        onChange={(e) => {
          const db = e.target.value || null;
          onSelect(db, null); // reset schema when db changes
        }}
        disabled={loading}
      >
        {loading ? (
          <option>Loading databases…</option>
        ) : (
          <>
            <option value="">Select a database…</option>
            {databases.map((db) => (
              <option key={db.name} value={db.name}>
                {db.name}
              </option>
            ))}
          </>
        )}
      </select>

      <label>Schema</label>
      <select
        value={selectedSchema || ''}
        onChange={(e) => {
          const schema = e.target.value || null;
          onSelect(selectedDatabase, schema);
        }}
        disabled={!selectedDatabase || schemasLoading}
      >
        {schemasLoading ? (
          <option>Loading schemas…</option>
        ) : !selectedDatabase ? (
          <option value="">Select a database first</option>
        ) : (
          <>
            <option value="">Select a schema…</option>
            {schemas.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </>
        )}
      </select>
    </div>
  );
}
