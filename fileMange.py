from metaconf.ac_metainfo_beehive import ACMetaBeehive
from metaconf.bs_metainfo_beehive import BSMetaBeehive

class MetafileMgr(object):
	def __init__(self, collector_name, meta_file):
		self.collector_name = collector_name
		self.meta_file = meta_file
		self.module = self._load_module_meta()

	def _load_module_meta(self):
		module = None
		if self.collector_name == 'ac':
			module = ACMetaBeehive(self.meta_file)

		elif self.collector_name == 'bs':
			module = BSMetaBeehive(self.meta_file)
			
		return module 
		
	
	def _get_result(self):
		work_path = None
		lidc = None
		pidc = None
		slot_library_dict = {}
		if self.module is not None:
			work_path, lidc, pidc, slot_library_dict = self.module.load()
	
			#work_path.append(rs)
		return work_path, lidc, pidc, slot_library_dict

if __name__ == '__main__':
	m = MetafileMgr('bs', '/home/work/agent/rm_meta_file')
	#TODO test
	#m = MetafileMgr('bs', '/home/work/opbin/gdcm/lib/metaconf/test/rm_meta_file')
	print m._get_result()

		 
