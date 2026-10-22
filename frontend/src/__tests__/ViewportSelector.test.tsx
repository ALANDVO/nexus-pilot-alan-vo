import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ViewportSelector } from '@/components/ViewportSelector'
import { useViewportSelection } from '@/hooks/useViewportSelection'
import * as THREE from 'three'

vi.mock('@/hooks/useViewportSelection')

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
    ;(useViewportSelection as vi.Mock).mockReturnValue(mockSelection)
  })

  it('renders canvas', () => {
    render(<ViewportSelector />)
    expect(screen.getByRole('canvas')).toBeInTheDocument()
  })

  it('calls setScene, setCamera, setRenderer on mount', () => {
    render(<ViewportSelector />)
    expect(mockSelection.setScene).toHaveBeenCalled()
    expect(mockSelection.setCamera).toHaveBeenCalled()
    expect(mockSelection.setRenderer).toHaveBeenCalled()
  })

  it('starts selection on mouse down', () => {
    render(<ViewportSelector />)
    const canvas = screen.getByRole('canvas')
    fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 })
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