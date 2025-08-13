_type)
        self.assertIn(ResourceType.MEMORY, self.agent.resources_by_type)
        self.assertIn(ResourceType.STORAGE, self.agent.resources_by_type)
        
        # Check resource values
        self.assertEqual(self.agent.resources_by_type[ResourceType.CPU], 8)
        self.assertEqual(self.agent.resources_by_type[ResourceType.MEMORY], 16 * 1024)  # 16 GB in MB
        self.assertEqual(self.agent.resources_by_type[ResourceType.STORAGE], 1024 * 1024)  # 1 TB in MB
    
    def test_subscribe_to_messages(self):
        """Test that agent subscribes to the correct message topics."""
        # Check that the agent subscribed to the right topics
        self.message_bus.subscribe.assert_any_call("system.resource.request", self.agent._handle_resource_request)
        self.message_bus.subscribe.assert_any_call("system.resource.release", self.agent._handle_resource_release)
        self.message_bus.subscribe.assert_any_call("system.component.started", self.agent._handle_component_started)
        self.message_bus.subscribe.assert_any_call("system.component.stopped", self.agent._handle_component_stopped)
    
    def test_resource_request_allocation(self):
        """Test that resource requests are properly allocated."""
        # Create a resource request
        request = ResourceRequest(
            component_id="test_component",
            resource_type=ResourceType.CPU,
            requested_amount=4.0,  # Request 4 CPU cores
            priority=Priority.NORMAL
        )
        
        # Process the request
        result = self.loop.run_until_complete(self.agent.handle_resource_request(request))
        
        # Check that the request was successful
        self.assertTrue(result.success)
        self.assertEqual(result.allocated_amount, 4.0)
        
        # Check that the component was added to tracking
        self.assertIn("test_component", self.agent.component_resources)
        self.assertIn(ResourceType.CPU, self.agent.component_resources["test_component"])
        self.assertEqual(self.agent.component_resources["test_component"][ResourceType.CPU].allocation, 4.0)
    
    def test_over_allocation_handling(self):
        """Test handling of requests that exceed available resources."""
        # Request more resources than available
        request = ResourceRequest(
            component_id="greedy_component",
            resource_type=ResourceType.CPU,
            requested_amount=10.0,  # More than the 8 cores available
            priority=Priority.NORMAL
        )
        
        # Process the request
        result = self.loop.run_until_complete(self.agent.handle_resource_request(request))
        
        # Check that the request was partially successful
        self.assertFalse(result.success)  # Should fail as we can't fully allocate
        self.assertLess(result.allocated_amount, 10.0)  # Should allocate less than requested
        self.assertGreater(result.allocated_amount, 0.0)  # But should allocate something
    
    def test_resource_release(self):
        """Test that resources are properly released."""
        # First allocate some resources
        request = ResourceRequest(
            component_id="temp_component",
            resource_type=ResourceType.MEMORY,
            requested_amount=1024.0,  # 1 GB
            priority=Priority.NORMAL
        )
        
        # Process the request
        _ = self.loop.run_until_complete(self.agent.handle_resource_request(request))
        
        # Check initial allocation
        self.assertEqual(self.agent.component_resources["temp_component"][ResourceType.MEMORY].allocation, 1024.0)
        
        # Create a release message
        release_message = {
            "component_id": "temp_component",
            "resource_type": "MEMORY",
            "request_id": "test-release-1"
        }
        
        # Process the release
        self.loop.run_until_complete(self.agent._handle_resource_release(release_message))
        
        # Check that the resource was released
        self.assertEqual(self.agent.component_resources["temp_component"][ResourceType.MEMORY].allocation, 0.0)
    
    def test_component_lifecycle(self):
        """Test handling of component lifecycle events."""
        # Component started event
        start_message = {
            "component_id": "lifecycle_component"
        }
        
        self.loop.run_until_complete(self.agent._handle_component_started(start_message))
        
        # Check that component was added to tracking
        self.assertIn("lifecycle_component", self.agent.component_resources)
        
        # Allocate some resources
        request = ResourceRequest(
            component_id="lifecycle_component",
            resource_type=ResourceType.CPU,
            requested_amount=2.0,
            priority=Priority.NORMAL
        )
        
        _ = self.loop.run_until_complete(self.agent.handle_resource_request(request))
        
        # Check that resource was allocated
        self.assertEqual(self.agent.component_resources["lifecycle_component"][ResourceType.CPU].allocation, 2.0)
        
        # Component stopped event
        stop_message = {
            "component_id": "lifecycle_component"
        }
        
        self.loop.run_until_complete(self.agent._handle_component_stopped(stop_message))
        
        # Check that component was removed from tracking
        self.assertNotIn("lifecycle_component", self.agent.component_resources)
    
    def test_resource_usage_history(self):
        """Test the ResourceUsageHistory class."""
        # Create a history object
        history = ResourceUsageHistory(
            component_id="test_component",
            resource_type=ResourceType.CPU
        )
        
        # Add some samples
        history.add_sample(0.5)  # 50% usage
        history.add_sample(0.6)  # 60% usage
        history.add_sample(0.7)  # 70% usage
        
        # Check average usage
        avg_usage = history.get_average_usage()
        self.assertAlmostEqual(avg_usage, 0.6, delta=0.1)  # Should be around 60%
        
        # Check peak usage
        peak_usage = history.get_peak_usage()
        self.assertEqual(peak_usage, 0.7)  # Should be 70%
        
        # Check trend (should be positive)
        trend = history.get_trend()
        self.assertGreater(trend, 0)  # Should show increasing trend
    
    def test_adjust_allocation(self):
        """Test the _adjust_allocation method."""
        # Set up a component with initial allocation
        component_id = "adjustment_test"
        self.agent.component_resources[component_id] = {}
        self.agent.component_resources[component_id][ResourceType.CPU] = ResourceUsageHistory(
            component_id=component_id,
            resource_type=ResourceType.CPU
        )
        self.agent.component_resources[component_id][ResourceType.CPU].allocation = 2.0
        
        # Adjust allocation up
        self.loop.run_until_complete(self.agent._adjust_allocation(
            component_id=component_id,
            resource_type=ResourceType.CPU,
            new_allocation=3.0
        ))
        
        # Check that allocation was increased
        self.assertEqual(self.agent.component_resources[component_id][ResourceType.CPU].allocation, 3.0)
        
        # Verify that a message was published with the new allocation
        self.message_bus.publish.assert_called_with(
            "system.resource.allocation",
            {
                "component_id": component_id,
                "resource_type": "CPU",
                "allocation": 3.0,
                "previous_allocation": 2.0
            }
        )
    
    def test_multiple_components(self):
        """Test managing resources across multiple components."""
        # Allocate resources to first component
        request1 = ResourceRequest(
            component_id="component1",
            resource_type=ResourceType.CPU,
            requested_amount=3.0,
            priority=Priority.NORMAL
        )
        
        result1 = self.loop.run_until_complete(self.agent.handle_resource_request(request1))
        
        # Allocate resources to second component
        request2 = ResourceRequest(
            component_id="component2",
            resource_type=ResourceType.CPU,
            requested_amount=3.0,
            priority=Priority.NORMAL
        )
        
        result2 = self.loop.run_until_complete(self.agent.handle_resource_request(request2))
        
        # Check that both allocations succeeded
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        
        # Check that resources were correctly allocated
        self.assertEqual(self.agent.component_resources["component1"][ResourceType.CPU].allocation, 3.0)
        self.assertEqual(self.agent.component_resources["component2"][ResourceType.CPU].allocation, 3.0)
        
        # Try to allocate more than remaining resources
        request3 = ResourceRequest(
            component_id="component3",
            resource_type=ResourceType.CPU,
            requested_amount=3.0,  # Only ~2 cores left (8 total, ~7.6 allocatable with 5% reserve)
            priority=Priority.NORMAL
        )
        
        result3 = self.loop.run_until_complete(self.agent.handle_resource_request(request3))
        
        # Check that the request was partially fulfilled
        self.assertFalse(result3.success)
        self.assertLess(result3.allocated_amount, 3.0)
        
        # Total allocation should not exceed ~7.6 cores (8 cores with 5% reserve)
        total_allocated = (
            self.agent.component_resources["component1"][ResourceType.CPU].allocation +
            self.agent.component_resources["component2"][ResourceType.CPU].allocation +
            self.agent.component_resources["component3"][ResourceType.CPU].allocation
        )
        
        self.assertLessEqual(total_allocated, 8.0 * 0.95 + 0.01)  # Allow tiny rounding error


if __name__ == "__main__":
    unittest.main()
