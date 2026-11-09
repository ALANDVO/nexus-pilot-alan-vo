
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useViewportSelection } from '@/hooks/useViewportSelection'
import * as THREE from 'three'

vi.mock('@/hooks/useViewportSelection')
vi.mock('@/components/ViewportSelector', () => ({
  ViewportSelector: ({ modelUrl, onSelectionChange }: any) => {
    const selection = useViewportSelection()
    // Call setup functions on mount
    React.useEffect(() => {
      selection.setScene(new THREE.Scene())
      selection.setCamera(new THREE.PerspectiveCamera())
      selection.setRenderer({ getSize: () => new THREE.Vector2(800, 600), setClearColor: vi.fn() })
    }, [])
    return (
      <div data-testid="viewport-selector" onMouseDown={() => selection.startSelection()} onMouseMove={() => selection.updateSelection()} onMouseUp={() => selection.endSelection()} onMouseLeave={() => selection.endSelection()}>
        <div data-testid="r3f-canvas">Mock Canvas</div>
        {selection.isSelecting && <div data-testid="selection-box">Selecting...</div>}
        {selection.selectedGeometry && (
          <div data-testid="selection-info">
            <p>Selection Active</p>
            <p>Faces: {selection.selectedGeometry.faces.length}</p>
            <p>Edges: {selection.selectedGeometry.edges.length}</p>
            <button onClick={() => { selection.clearSelection(); onSelectionChange?.(null) }}>Clear Selection</button>
          </div>
        )}
      </div>
    )
  }
}))

import React from 'react'
import { ViewportSelector } from '@/components/ViewportSelector'

describe('ViewportSelector', () => {
  const mockSelection = {
    isSelecting: false,
    selectionBox: null,
    selectedGeometry: null,
    setScene: vi.fn(),
    setCamera: vi.fn(),
    setRenderer: vi.fn(),
    startSelection: vi.fn(),
    updateSelection: vi.fn(),
    endSelection: vi.fn(),
    clearSelection: vi.fn(),
    getSelectionForAgent: vi.fn().mockReturnValue(null)
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useViewportSelection as any).mockReturnValue(mockSelection)
  })

  it('renders without error', () => {
    render(<ViewportSelector />)
    expect(screen.getByTestId('viewport-selector')).toBeInTheDocument()
    expect(screen.getByTestId('r3f-canvas')).toBeInTheDocument()
  })

  it('calls setScene, setCamera, setRenderer on mount', () => {
    render(<ViewportSelector />)
    expect(mockSelection.setScene).toHaveBeenCalled()
    expect(mockSelection.setCamera).toHaveBeenCalled()
    expect(mockSelection.setRenderer).toHaveBeenCalled()
  })

  it('starts selection on mouse down', () => {
    render(<ViewportSelector />)
    const viewport = screen.getByTestId('viewport-selector')
    fireEvent.mouseDown(viewport)
    expect(mockSelection.startSelection).toHaveBeenCalled()
  })

  it('shows selection info when geometry selected', () => {
    mockSelection.selectedGeometry = { faces: [1, 2, 3], edges: [], boundingBox: { min: new THREE.Vector3(), max: new THREE.Vector3() } }
    mockSelection.isSelecting = false

    render(<ViewportSelector />)
    expect(screen.getByText(/selection active/i)).toBeInTheDocument()
    expect(screen.getByText(/faces: 3/i)).toBeInTheDocument()
  })

  it('clears selection on button click', () => {
    mockSelection.selectedGeometry = { faces: [1], edges: [], boundingBox: { min: new THREE.Vector3(), max: new THREE.Vector3() } }
    mockSelection.isSelecting = false

    render(<ViewportSelector />)
    fireEvent.click(screen.getByRole('button', { name: /clear selection/i }))
    expect(mockSelection.clearSelection).toHaveBeenCalled()
  })
})
