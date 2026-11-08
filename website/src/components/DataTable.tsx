'use client';

import React, { useState } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  SortingState,
  useReactTable
} from '@tanstack/react-table';
import { Search, ChevronDown, ChevronUp, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchPlaceholder?: string;
  searchColumnKey?: string;
  categoryFilterKey?: string;
  categories?: { label: string; value: string }[];
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchPlaceholder = 'Search records...',
  searchColumnKey,
  categoryFilterKey,
  categories = []
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const filteredData = React.useMemo(() => {
    if (!categoryFilterKey || selectedCategory === 'all') {
      return data;
    }
    return data.filter((item: any) => item[categoryFilterKey] === selectedCategory);
  }, [data, categoryFilterKey, selectedCategory]);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      globalFilter
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 10
      }
    }
  });

  return (
    <div className="space-y-4">
      {/* Search and Category Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden="true" />
          <input
            type="text"
            value={globalFilter ?? ''}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder}
            className="w-full pl-9 pr-4 py-2 text-xs bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] rounded-lg text-[#0E1415] dark:text-[#F2F5F5] placeholder-[#526063] dark:placeholder-[#98A8AA] focus:outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
          />
        </div>

        {/* Category Pills */}
        {categories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs" role="group" aria-label="Category filters">
            <button
              onClick={() => setSelectedCategory('all')}
              aria-pressed={selectedCategory === 'all'}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                selectedCategory === 'all'
                  ? 'bg-[#E6F3F4] text-[#006D77] dark:bg-[#0D2C28] dark:text-[#2DD4BF] border border-[#006D77]/30 dark:border-[#2DD4BF]/40 font-semibold'
                  : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#ECEEED] dark:hover:bg-[#1D2629]'
              }`}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value)}
                aria-pressed={selectedCategory === cat.value}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  selectedCategory === cat.value
                    ? 'bg-[#E6F3F4] text-[#006D77] dark:bg-[#0D2C28] dark:text-[#2DD4BF] border border-[#006D77]/30 dark:border-[#2DD4BF]/40 font-semibold'
                    : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#ECEEED] dark:hover:bg-[#1D2629]'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Table Container */}
      <div className="rounded-xl border border-[#E2E5E5] dark:border-[#242F32] bg-white dark:bg-[#121719] overflow-x-auto shadow-sm">
        <table className="w-full text-left border-collapse text-xs" aria-label="Research data table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-[#E2E5E5] dark:border-[#242F32] bg-[#F5F5F3] dark:bg-[#182022]">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-semibold uppercase tracking-wider text-[11px]"
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={
                          header.column.getCanSort()
                            ? 'flex items-center gap-1.5 cursor-pointer select-none hover:text-[#006D77] dark:hover:text-[#2DD4BF]'
                            : ''
                        }
                        onClick={header.column.getToggleSortingHandler()}
                        role={header.column.getCanSort() ? 'button' : undefined}
                        tabIndex={header.column.getCanSort() ? 0 : undefined}
                        onKeyDown={(e) => {
                          if (header.column.getCanSort() && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault();
                            header.column.toggleSorting();
                          }
                        }}
                        aria-label={
                          header.column.getCanSort()
                            ? `Sort by ${String(header.column.columnDef.header)}`
                            : undefined
                        }
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getCanSort() && (
                          <span className="text-slate-400">
                            {{
                              asc: <ChevronUp className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />,
                              desc: <ChevronDown className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
                            }[header.column.getIsSorted() as string] ?? (
                              <ChevronsUpDown className="w-3.5 h-3.5 opacity-40" aria-hidden="true" />
                            )}
                          </span>
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="py-3 px-4 text-slate-800 dark:text-slate-200">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="h-24 text-center text-slate-500 dark:text-slate-400">
                  No records matching the filter criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300 px-1">
        <div>
          Showing {table.getRowModel().rows.length} of {filteredData.length} records
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label="Go to previous page"
            className="p-1.5 rounded bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </button>
          <span>
            Page {table.getState().pagination.pageIndex + 1} of {Math.max(1, table.getPageCount())}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            aria-label="Go to next page"
            className="p-1.5 rounded bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default DataTable;
